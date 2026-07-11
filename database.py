import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# 1. On regarde si Railway (ou toi en local) fournit l'URL complète d'un coup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Si elle n'existe pas, on la reconstruit avec tes variables découpées du .env local
if not SQLALCHEMY_DATABASE_URL:
    PGUSER = os.getenv("PGUSER")
    PGPASSWORD = os.getenv("PGPASSWORD")
    PGHOST = os.getenv("PGHOST")
    PGDATABASE = os.getenv("PGDATABASE")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}/{PGDATABASE}?sslmode=require"

# 3. Sécurité Railway : s'assurer que ça commence par postgresql:// et non postgres://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Le reste de ton code reste strictement identique et super propre !
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()