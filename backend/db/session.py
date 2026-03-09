import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_database_url() -> str:
    local_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "data")
    local_db_path = os.path.join(local_data_dir, "games.db")
    
    # Check if we are inside docker
    if os.path.exists("/app"):
        db_url = os.getenv("DATABASE_URL", "sqlite:////app/data/games.db")
        if db_url.startswith("sqlite:////"):
            return db_url.replace("sqlite:////", "sqlite:///")
        return db_url
        
    # We are running locally on the host machine
    os.makedirs(local_data_dir, exist_ok=True)
    return f"sqlite:///{local_db_path.replace(chr(92), '/')}"

engine = create_engine(get_database_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    """Dependency to provide a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
