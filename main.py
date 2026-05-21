import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager
from database import engine, Base
import models
from routers import auth, mushrooms, identification, cart, orders, notifications, home, chat

if hasattr(sys, 'base_prefix') and sys.prefix == sys.base_prefix:
    print(
        "WARNING: You are not running inside a virtual environment. "
        "Use .venv\\Scripts\\activate (Windows) or .venv/bin/activate (macOS/Linux), "
        "or run .venv\\Scripts\\python.exe main.py."
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Mushroom Project API",
    description="Backend API for mushroom identification, classification, and marketplace",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images (mushroom identification photos)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(mushrooms.router, prefix="/api/mushrooms", tags=["Mushrooms"])
app.include_router(identification.router, prefix="/api/identify", tags=["Identification"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(home.router, prefix="/api/home", tags=["Home Content"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chatbot"])


@app.get("/")
def root():
    return {"message": "Mushroom Project API is running", "docs": "/docs"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
