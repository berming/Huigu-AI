from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.market import router as market_router
from app.api.sentiment import router as sentiment_router
from app.api.ai import router as ai_router

app = FastAPI(
    title="慧股AI Backend",
    description="HuiGu AI — Chinese A-share investment intelligence platform API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)
app.include_router(sentiment_router)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "慧股AI Backend"}


@app.get("/")
def root():
    return {
        "name": "慧股AI API",
        "version": "1.0.0",
        "docs": "/docs",
    }
