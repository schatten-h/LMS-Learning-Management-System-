from database import engine, Base
import models  # Important pour charger tous les modèles avant la suppression

def reset_database():
    print("⚠️ Suppression des anciennes tables en cours...")
    Base.metadata.drop_all(bind=engine)
    print("🚀 Création des nouvelles tables avec les bonnes colonnes...")
    Base.metadata.create_all(bind=engine)
    print("✅ Base de données réinitialisée avec succès !")

if __name__ == "__main__":
    reset_database()