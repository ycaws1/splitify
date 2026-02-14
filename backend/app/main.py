from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.groups import router as groups_router
from app.api.receipts import router as receipts_router
from app.api.assignments import router as assignments_router

app = FastAPI(title="Splitify API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(receipts_router)
app.include_router(assignments_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
