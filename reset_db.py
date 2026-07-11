from sqlalchemy import text
from database import engine, Base
import models  

def reset_database():
    print("⚠️ Suppression brutale des anciennes tables en cours (CASCADE)...")
    
    # On force la suppression de TOUTES les tables possibles, y compris l'ancienne table "quizzes"
    with engine.connect() as conn:
        conn.execute(text("""
            DROP TABLE IF EXISTS 
            quizzes, certificates, enrollments, choices, questions, lessons, courses, modules, users 
            CASCADE;
        """))
        conn.commit()

    print("🚀 Création des nouvelles tables avec les bonnes colonnes...")
    Base.metadata.create_all(bind=engine)
    print("✅ Base de données réinitialisée avec succès !")

if __name__ == "__main__":
    reset_database()