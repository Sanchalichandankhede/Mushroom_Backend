from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Default to a local SQLite database when DATABASE_URL is not provided.
# This keeps the backend runnable out of the box.
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./mushroom_project.db"

# Supabase requires a slightly different connection string format for some libraries.
# If it starts with postgres:// we need to change it to postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs a special connect arg when using SQLAlchemy with FastAPI.
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite:"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
