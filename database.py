import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Récupération de vos variables
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGHOST = os.getenv("PGHOST")
PGDATABASE = os.getenv("PGDATABASE")

# Reconstitution de l'URL avec SSL requis
SQLALCHEMY_DATABASE_URL = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}/{PGDATABASE}?sslmode=require"

# pool_pre_ping=True évite les crashs dus aux déconnexions SSL intempestives des bases Serverless
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()