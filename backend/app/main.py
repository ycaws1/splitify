import asyncio
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

import os

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

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
