from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.routes import predict
from app.routes import comments
# from app.routes import likes
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.routes import posts
from app.routes import auth
import os
from dotenv import load_dotenv
from app.scheduler import start_scheduler
from contextlib import asynccontextmanager
from app.services.model_service import load_model, cleanup_model
from app.scheduler import start_scheduler
from app.database import Base
import threading


load_dotenv()

ENV = os.getenv("ENV", "dev")


origins = (
    ["http://localhost:3000","*","https://truthlens.manvendrasingh.net.in"]
)

print(origins)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    thread = threading.Thread(target=load_model, daemon=True)
    thread.start()

    start_scheduler()

    yield

    # Shutdown
    cleanup_model()

app = FastAPI(
    title="TruthLens API",
    description="AI-powered fake news detection and community feed platform",
    version="1.0.0",
    lifespan=lifespan
)


# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # later restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(predict.router)
app.include_router(posts.router)
app.include_router(auth.router)
app.include_router(comments.router)


@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    return {"status": "database connected"}


@app.get("/")
def root():
    return {
        "message": "TruthLens API is running",
        "docs": "/docs"
    }


@app.get("/kaithhealth")
def health_check():
    return {"status": "healthy"}
