"""Valtimo ExApp - Nextcloud External Application wrapper for Valtimo BPM."""

import asyncio
import logging
import os
import subprocess
import threading
import typing
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import nc_app, run_app, setup_nextcloud_logging
from nc_py_api.ex_app.integration_fastapi import AppAPIAuthMiddleware


# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="[%(funcName)s]: %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger("valtimo")
LOGGER.setLevel(logging.DEBUG)


# ── Configuration ───────────────────────────────────────────────────
APP_ID = os.environ.get("APP_ID", "valtimo")
VALTIMO_PORT = int(os.environ.get("VALTIMO_PORT", "8080"))
VALTIMO_PROCESS = None

# Detect HaRP mode and set proxy prefix accordingly
HARP_ENABLED = bool(os.environ.get("HP_SHARED_KEY"))
if HARP_ENABLED:
    PROXY_PREFIX = f"/exapps/{APP_ID}"
else:
    PROXY_PREFIX = f"/index.php/apps/app_api/proxy/{APP_ID}"

# Keycloak/OIDC configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "commonground")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "valtimo")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


# ── OIDC ───────────────────────────────────────────────────────────
def get_oidc_env() -> dict:
    """Get OIDC environment variables for Spring Boot if Keycloak is configured."""
    if not KEYCLOAK_URL:
        return {}

    oidc_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
    return {
        "KEYCLOAK_AUTH_SERVER_URL": KEYCLOAK_URL,
        "KEYCLOAK_REALM": KEYCLOAK_REALM,
        "KEYCLOAK_RESOURCE": KEYCLOAK_CLIENT_ID,
        "KEYCLOAK_CREDENTIALS_SECRET": KEYCLOAK_CLIENT_SECRET,
        "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI": oidc_url,
        "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_JWK_SET_URI": f"{oidc_url}/protocol/openid-connect/certs",
        "VALTIMO_OAUTH_PUBLIC_KEY": f"{oidc_url}/protocol/openid-connect/certs",
    }


# ── Process Management ─────────────────────────────────────────────
def start_valtimo():
    """Start the Valtimo Spring Boot service."""
    global VALTIMO_PROCESS
    if VALTIMO_PROCESS is not None and VALTIMO_PROCESS.poll() is None:
        return

    env = os.environ.copy()
    java_opts = env.get("JAVA_OPTS", "-Xmx512m -Xms256m").split()
    env.update(get_oidc_env())

    cmd = ["java"] + java_opts + ["-jar", "/app/valtimo.jar"]
    VALTIMO_PROCESS = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    def log_output():
        for line in VALTIMO_PROCESS.stdout:
            LOGGER.info("[valtimo] %s", line.decode().strip())

    threading.Thread(target=log_output, daemon=True).start()
    LOGGER.info("Valtimo started with PID: %d", VALTIMO_PROCESS.pid)


def stop_valtimo():
    """Stop the Valtimo service."""
    global VALTIMO_PROCESS
    if VALTIMO_PROCESS is not None:
        VALTIMO_PROCESS.terminate()
        try:
            VALTIMO_PROCESS.wait(timeout=30)
        except subprocess.TimeoutExpired:
            VALTIMO_PROCESS.kill()
        VALTIMO_PROCESS = None
        LOGGER.info("Valtimo stopped")


async def wait_for_valtimo(timeout: int = 180) -> bool:
    """Wait for Valtimo to become healthy (Spring Boot takes time to start)."""
    for _ in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://localhost:{VALTIMO_PORT}/actuator/health",
                    timeout=2,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "UP":
                        return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


# ── Lifespan ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_nextcloud_logging("valtimo", logging_level=logging.WARNING)
    LOGGER.info("Starting Valtimo ExApp")
    yield
    stop_valtimo()
    LOGGER.info("Valtimo ExApp shutdown complete")


# ── FastAPI App ─────────────────────────────────────────────────────
APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)


# ── Inline iframe loader JS ────────────────────────────────────────
IFRAME_LOADER_JS = f"""
(function() {{
    var style = document.createElement('style');
    style.textContent =
        '#content.app-app_api {{' +
        '  margin-top: var(--header-height) !important;' +
        '  height: var(--body-height) !important;' +
        '  width: calc(100% - var(--body-container-margin) * 2) !important;' +
        '  border-radius: var(--body-container-radius) !important;' +
        '  overflow: hidden !important;' +
        '  padding: 0 !important;' +
        '}}' +
        '#content.app-app_api > iframe {{ width: 100%; height: 100%; border: none; display: block; }}';
    document.head.appendChild(style);

    function setup() {{
        var content = document.getElementById('content');
        if (!content) return;
        content.innerHTML = '';
        var iframe = document.createElement('iframe');
        iframe.src = '{PROXY_PREFIX}/';
        iframe.allow = 'clipboard-read; clipboard-write';
        content.appendChild(iframe);
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', setup);
    }} else {{
        setup();
    }}
}})();
""".strip()


@APP.get("/js/valtimo-iframe-loader.js")
async def iframe_loader():
    """Serve the inline iframe loader script."""
    return Response(
        content=IFRAME_LOADER_JS,
        media_type="application/javascript",
    )


# ── Enabled Handler ────────────────────────────────────────────────
def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    """Handle app enable/disable events."""
    if enabled:
        LOGGER.info("Enabling Valtimo ExApp")
        nc.ui.resources.set_script("top_menu", "valtimo", "js/valtimo-iframe-loader")
        nc.ui.top_menu.register("valtimo", "Valtimo", "img/app.svg", True)
        start_valtimo()
    else:
        LOGGER.info("Disabling Valtimo ExApp")
        nc.ui.resources.delete_script("top_menu", "valtimo", "js/valtimo-iframe-loader")
        nc.ui.top_menu.unregister("valtimo")
        stop_valtimo()
    return ""


# ── Required Endpoints ──────────────────────────────────────────────
@APP.get("/heartbeat")
async def heartbeat():
    """Heartbeat endpoint for AppAPI health checks."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://localhost:{VALTIMO_PORT}/actuator/health",
                timeout=5,
            )
            if resp.status_code == 200:
                return JSONResponse({"status": "ok"})
    except Exception:
        pass
    return JSONResponse({"status": "waiting"})


@APP.post("/init")
async def init_callback(
    b_tasks: BackgroundTasks,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Initialization endpoint called by AppAPI after installation."""
    b_tasks.add_task(init_task, nc)
    return JSONResponse(content={})


@APP.put("/enabled")
def enabled_callback(
    enabled: bool,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Enable/disable callback from AppAPI."""
    return JSONResponse(content={"error": enabled_handler(enabled, nc)})


async def init_task(nc: NextcloudApp):
    """Background task for Valtimo initialization with progress reporting."""
    nc.set_init_status(0)
    LOGGER.info("Starting Valtimo initialization...")

    nc.set_init_status(10)
    start_valtimo()

    if await wait_for_valtimo():
        nc.set_init_status(80)
        nc.ui.resources.set_script("top_menu", "valtimo", "js/valtimo-iframe-loader")
        nc.ui.top_menu.register("valtimo", "Valtimo", "img/app.svg", True)
        nc.set_init_status(100)
        LOGGER.info("Valtimo initialization complete")
    else:
        LOGGER.error("Valtimo failed to start within timeout")


# ── Catch-All Proxy ────────────────────────────────────────────────
@APP.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy(request: Request, path: str):
    """Proxy all requests to Valtimo."""
    # Serve ex_app static files (icons, JS) directly from disk
    if path.startswith(("ex_app/", "img/")):
        file_path = Path(__file__).parent.parent.parent / path
        if file_path.is_file():
            from starlette.responses import FileResponse

            return FileResponse(str(file_path))

    try:
        async with httpx.AsyncClient() as client:
            url = f"http://localhost:{VALTIMO_PORT}/{path}"

            resp = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers={
                    k: v
                    for k, v in request.headers.items()
                    if k.lower()
                    not in ("host", "connection", "transfer-encoding", "accept-encoding")
                },
                params=request.query_params,
                timeout=60,
            )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower()
                    not in ("content-encoding", "transfer-encoding", "content-length")
                },
            )
    except httpx.RequestError as e:
        LOGGER.error("Proxy error: %s", str(e))
        return JSONResponse(
            {"error": f"Proxy error: {str(e)}"},
            status_code=502,
        )


# ── Entry Point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    run_app(APP, log_level="info")
