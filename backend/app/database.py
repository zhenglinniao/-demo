from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

connect_args = {}
db_url = DATABASE_URL
if db_url.startswith("sqlite"):
    if db_url.startswith("sqlite:///./"):
        db_path = db_url.replace("sqlite:///./", "")
        abs_path = Path(__file__).resolve().parent / db_path
        db_url = f"sqlite:///{abs_path.as_posix()}"
    connect_args = {"check_same_thread": False}

engine = create_engine(db_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
