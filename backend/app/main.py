import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.groups import router as groups_router
from app.api.receipts import router as receipts_router
from app.api.assignments import router as assignments_router
from app.api.payments import router as payments_router
from app.api.stats import router as stats_router
from app.api.push import router as push_router
from app.workers.reminders import send_overdue_reminders


async def reminder_loop():
    while True:
        try:
            await send_overdue_reminders()
        except Exception:
            pass  # don't crash the loop
        await asyncio.sleep(86400)  # run daily


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()


app = FastAPI(title="Splitify API", version="0.1.0", lifespan=lifespan)

from app.core.config import settings

cors_origins = settings.cors_origins.split(",")

from starlette.types import ASGIApp, Receive, Scope, Send

class TimingMiddleware:
    """Lightweight ASGI middleware — no BaseHTTPMiddleware overhead."""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        t0 = time.perf_counter()
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        ms = int((time.perf_counter() - t0) * 1000)
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        qs = scope.get("query_string", b"").decode()
        qs_str = f"?{qs}" if qs else ""
        print(f"TIMING: {method} {path}{qs_str} -> {status_code} in {ms}ms")


app.add_middleware(TimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(receipts_router)
app.include_router(assignments_router)
app.include_router(payments_router)
app.include_router(stats_router)
app.include_router(push_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
