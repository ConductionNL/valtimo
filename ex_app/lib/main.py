"""
Valtimo ExApp - FastAPI wrapper for Nextcloud AppAPI integration

Valtimo is a less-code platform for Business Process Automation.
See: https://docs.valtimo.nl/
"""
import os
import subprocess
import asyncio
import base64
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, Response

# Environment variables set by AppAPI
APP_ID = os.environ.get("APP_ID", "valtimo")
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")
APP_SECRET = os.environ.get("APP_SECRET", "")
APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("APP_PORT", "9000"))
NEXTCLOUD_URL = os.environ.get("NEXTCLOUD_URL", "http://nextcloud")

# Valtimo configuration - Spring Boot app runs on 8080
VALTIMO_PORT = int(os.environ.get("VALTIMO_PORT", "8080"))
VALTIMO_PROCESS = None

# Keycloak/OIDC configuration
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "commonground")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "valtimo")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


def get_auth_header() -> dict:
    """Generate AppAPI authentication header"""
    auth = base64.b64encode(f":{APP_SECRET}".encode()).decode()
    return {
        "EX-APP-ID": APP_ID,
        "EX-APP-VERSION": APP_VERSION,
        "AUTHORIZATION-APP-API": auth,
    }


async def report_status(progress: int) -> None:
    """Report initialization progress to Nextcloud"""
    try:
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{NEXTCLOUD_URL}/ocs/v1.php/apps/app_api/apps/status",
                headers=get_auth_header(),
                json={"progress": progress},
                timeout=10,
            )
    except Exception as e:
        print(f"Failed to report status: {e}")


def get_oidc_env() -> dict:
    """Get OIDC environment variables for Spring Boot if Keycloak is configured"""
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
        "SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_JWK_SET_URI": f"{oidc_url}/protocol/openid-connect/certs",
        # Valtimo specific Keycloak settings
        "VALTIMO_OAUTH_PUBLIC_KEY": f"{oidc_url}/protocol/openid-connect/certs",
    }


def start_valtimo() -> None:
    """Start the Valtimo Spring Boot service"""
    global VALTIMO_PROCESS
    if VALTIMO_PROCESS is not None:
        return

    env = os.environ.copy()
    java_opts = env.get("JAVA_OPTS", "-Xmx512m -Xms256m").split()

    # Add OIDC configuration if Keycloak is configured
    env.update(get_oidc_env())
    if KEYCLOAK_URL:
        print(f"OIDC configured with Keycloak at {KEYCLOAK_URL}")

    # Start Valtimo (Spring Boot JAR)
    cmd = ["java"] + java_opts + ["-jar", "/app/valtimo.jar"]
    VALTIMO_PROCESS = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
    )
    print(f"Valtimo started with PID: {VALTIMO_PROCESS.pid}")


def stop_valtimo() -> None:
    """Stop the Valtimo service"""
    global VALTIMO_PROCESS
    if VALTIMO_PROCESS is not None:
        VALTIMO_PROCESS.terminate()
        try:
            VALTIMO_PROCESS.wait(timeout=30)
        except subprocess.TimeoutExpired:
            VALTIMO_PROCESS.kill()
        VALTIMO_PROCESS = None
        print("Valtimo stopped")


async def wait_for_valtimo(timeout: int = 180) -> bool:
    """Wait for Valtimo to become healthy (Spring Boot takes time to start)"""
    for _ in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                # Spring Boot actuator health endpoint
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print(f"Valtimo ExApp starting on {APP_HOST}:{APP_PORT}")
    yield
    stop_valtimo()
    print("Valtimo ExApp shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.get("/heartbeat")
async def heartbeat():
    """Health check endpoint for AppAPI"""
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


@app.post("/init")
async def init(background_tasks: BackgroundTasks):
    """Initialization endpoint called by AppAPI during deployment"""
    async def do_init():
        await report_status(0)
        print("Starting Valtimo initialization...")

        await report_status(10)
        start_valtimo()

        await report_status(30)
        # Valtimo/Spring Boot takes longer to start
        if await wait_for_valtimo(timeout=180):
            await report_status(100)
            print("Valtimo initialization complete")
        else:
            print("Valtimo failed to start - check configuration")
            await report_status(0)

    background_tasks.add_task(do_init)
    return JSONResponse({"status": "init_started"})


@app.put("/enabled")
async def enabled(request: Request):
    """Enable/disable endpoint called by AppAPI"""
    data = await request.json()
    is_enabled = data.get("enabled", False)

    if is_enabled:
        start_valtimo()
        await wait_for_valtimo(timeout=120)
    else:
        stop_valtimo()

    return JSONResponse({"status": "ok"})


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str):
    """Proxy all other requests to Valtimo"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"http://localhost:{VALTIMO_PORT}/{path}"

            resp = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers={
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ("host", "content-length")
                },
                params=request.query_params,
                timeout=60,
            )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers={
                    k: v for k, v in resp.headers.items()
                    if k.lower() not in ("content-encoding", "transfer-encoding")
                },
            )
    except httpx.RequestError as e:
        return JSONResponse(
            {"error": f"Proxy error: {str(e)}"},
            status_code=502,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
