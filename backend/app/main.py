from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import advice, interactions, normalize, review


app = FastAPI(title="Medical Interaction Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(normalize.router, prefix="/medications", tags=["medications"])
app.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
app.include_router(advice.router, prefix="/advice", tags=["advice"])
app.include_router(review.router, prefix="/cases", tags=["cases"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
