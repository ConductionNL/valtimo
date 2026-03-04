"""Valtimo ExApp - Nextcloud External Application wrapper for Valtimo BPM/case management.

Valtimo is a less-code platform for Business Process Automation built on Camunda.
See: https://docs.valtimo.nl/
"""

import asyncio
import logging
import os
import subprocess
import threading
import typing
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import (
    nc_app,
    run_app,
    setup_nextcloud_logging,
)
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
VALTIMO_PORT = 8080
VALTIMO_URL = f"http://localhost:{VALTIMO_PORT}"
VALTIMO_PROCESS = None

APP_ID = os.environ.get("APP_ID", "valtimo")

# Keycloak/OIDC configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "commonground")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "valtimo")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


# ── OIDC Environment ───────────────────────────────────────────────
def get_oidc_env() -> dict:
    """Get OIDC environment variables for Spring Boot if Keycloak is configured."""
    if not KEYCLOAK_URL:
        return {}

    oidc_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
    return {
        # Spring Security OAuth2 / Keycloak settings
        "KEYCLOAK_AUTH_SERVER_URL": KEYCLOAK_URL,
        "KEYCLOAK_REALM": KEYCLOAK_REALM,
        "KEYCLOAK_RESOURCE": KEYCLOAK_CLIENT_ID,
        "KEYCLOAK_CREDENTIALS_SECRET": KEYCLOAK_CLIENT_SECRET,
        # Spring Boot OAuth2 Resource Server
        "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI": oidc_url,
        "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_JWK_SET_URI": (
            f"{oidc_url}/protocol/openid-connect/certs"
        ),
        # Valtimo specific Keycloak settings
        "VALTIMO_OAUTH_PUBLIC_KEY": f"{oidc_url}/protocol/openid-connect/certs",
    }


# ── Valtimo Process Management ─────────────────────────────────────
def start_valtimo() -> None:
    """Start the Valtimo Spring Boot service."""
    global VALTIMO_PROCESS

    if VALTIMO_PROCESS is not None and VALTIMO_PROCESS.poll() is None:
        return

    env = os.environ.copy()
    java_opts = env.get("JAVA_OPTS", "-Xmx512m -Xms256m").split()

    # Add OIDC configuration if Keycloak is configured
    env.update(get_oidc_env())
    if KEYCLOAK_URL:
        LOGGER.info("OIDC configured with Keycloak at %s", KEYCLOAK_URL)

    cmd = ["java", *java_opts, "-jar", "/app/valtimo.jar"]
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


def stop_valtimo() -> None:
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
                    f"{VALTIMO_URL}/actuator/health",
                    timeout=5,
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


# ── Enabled Handler ────────────────────────────────────────────────
def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    """Handle app enable/disable events."""
    if enabled:
        LOGGER.info("Enabling Valtimo ExApp")
        start_valtimo()
    else:
        LOGGER.info("Disabling Valtimo ExApp")
        stop_valtimo()
    return ""


# ── Required Endpoints ──────────────────────────────────────────────
@APP.get("/heartbeat")
async def heartbeat_callback():
    """Heartbeat endpoint for AppAPI health checks."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{VALTIMO_URL}/actuator/health",
                timeout=5,
            )
            if resp.status_code == 200:
                return JSONResponse(content={"status": "ok"})
    except Exception:
        pass
    return JSONResponse(content={"status": "error"}, status_code=503)


@APP.post("/init")
async def init_callback(
    b_tasks: BackgroundTasks,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Initialization endpoint called by AppAPI after installation."""
    b_tasks.add_task(init_valtimo_task, nc)
    return JSONResponse(content={})


@APP.put("/enabled")
def enabled_callback(
    enabled: bool,
    nc: typing.Annotated[NextcloudApp, Depends(nc_app)],
):
    """Enable/disable callback from AppAPI."""
    return JSONResponse(content={"error": enabled_handler(enabled, nc)})


async def init_valtimo_task(nc: NextcloudApp):
    """Background task for Valtimo initialization with progress reporting."""
    nc.set_init_status(0)
    LOGGER.info("Starting Valtimo initialization...")

    start_valtimo()
    nc.set_init_status(20)

    if await wait_for_valtimo(timeout=180):
        nc.set_init_status(80)
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
    # Build headers, stripping hop-by-hop headers
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower()
        not in (
            "host",
            "connection",
            "transfer-encoding",
            "accept-encoding",
        )
    }

    try:
        async with httpx.AsyncClient() as client:
            url = f"{VALTIMO_URL}/{path}"

            resp = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers=headers,
                params=request.query_params,
                timeout=60,
            )

            # Forward response headers, filtering problematic ones
            resp_headers = {
                k: v
                for k, v in resp.headers.items()
                if k.lower()
                not in (
                    "content-encoding",
                    "transfer-encoding",
                    "content-length",
                )
            }

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers,
            )
    except httpx.RequestError as e:
        LOGGER.error("Proxy error: %s", str(e))
        return JSONResponse(
            {"error": f"Proxy error: {str(e)}"},
            status_code=502,
        )


# ── Entry Point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path

    os.chdir(Path(__file__).parent)
    run_app(APP, log_level="info")
