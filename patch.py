# patch.py
from sqlalchemy import text
from database import engine 

with engine.connect() as conn:
    print("Mise à jour de la table 'users' en cours...")
    conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
    conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255);"))
    conn.commit()
    print("✅ Base de données mise à jour avec succès !")

with engine.connect() as conn:
    print("Ajout de la colonne 'status' dans la table 'enrollments'...")
    # Remplacement de 'en cours' par 'in_progress' pour correspondre au modèle
    conn.execute(text("ALTER TABLE enrollments ADD COLUMN status VARCHAR(50) DEFAULT 'in_progress';"))
    conn.commit()
    print("✅ Table 'enrollments' mise à jour avec succès !")

with engine.connect() as conn:
    print("Ajout de la colonne 'enrolled_at'...")
    conn.execute(text("ALTER TABLE enrollments ADD COLUMN enrolled_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
    conn.commit()
    print("✅ Table 'enrollments' mise à jour avec la date !")

with engine.connect() as conn:
    print("Ajout de la colonne 'course_id' dans la table 'certificates'...")
    conn.execute(text("ALTER TABLE certificates ADD COLUMN course_id INTEGER;"))
    conn.commit()
    print("✅ Table 'certificates' mise à jour avec succès !")