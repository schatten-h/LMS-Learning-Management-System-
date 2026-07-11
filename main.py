import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import engine, Base, get_db

# Importation de tes routeurs fraîchement refactorisés et sécurisés
from routers import auth, enseignant, etudiant, promoteur, certificate
from routers.auth import get_current_user

# Création automatique des tables dans ta base de données Neon
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LMS API - Plateforme d'Apprentissage",
    description="API robuste intégrant une gestion stricte des rôles (Promoteur, Enseignant, Étudiant) et un moteur de notation 70/30.",
    version="1.0.0"
)

# Création des dossiers d'upload s'ils n'existent pas encore
os.makedirs(os.path.join("uploads", "pdfs"), exist_ok=True)
os.makedirs(os.path.join("uploads", "videos"), exist_ok=True)

# Montage du dossier 'static' pour charger le CSS, JS et HTML
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass # Ignore si le dossier /static n'est pas encore créé au lancement

# Montage du dossier 'uploads' pour lire les PDF et Vidéos depuis le Front-End
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except RuntimeError:
    pass

# 1. ROUTES BACKEND (API RESTful)
# L'harmonie est désormais totale : les préfixes URL matchent les rôles !

app.include_router(auth.router, prefix="/api/auth", tags=["Authentification"])
app.include_router(promoteur.router, prefix="/api/promoteur", tags=["Espace Promoteur"])
app.include_router(enseignant.router, prefix="/api/enseignant", tags=["Espace Enseignant"])
app.include_router(etudiant.router, prefix="/api/etudiant", tags=["Espace Étudiant"])

# Optionnel : Si tu as conservé un routeur séparé pour la validation publique des certificats
if hasattr(certificate, "router"):
    app.include_router(certificate.router, prefix="/api/certificate", tags=["Certificats"]) 


# 2. ROUTES FRONTEND (PAGES HTML)

@app.get("/", response_class=FileResponse, tags=["Pages Front-End"])
def home_page(): 
    return "static/login.html"

@app.get("/login", response_class=FileResponse, tags=["Pages Front-End"])
def login_page():
    return "static/login.html"

@app.get("/register", response_class=FileResponse, tags=["Pages Front-End"])
def register_page():
    return "static/register.html"

@app.get("/promoteur", response_class=FileResponse, tags=["Pages Front-End"])
def promoteur_page():
    # Pense bien à renommer ton fichier 'admin.html' en 'promoteur.html' dans ton dossier 'static' !
    return "static/promoteur.html"

@app.get("/enseignant", response_class=FileResponse, tags=["Pages Front-End"])
def teacher_page():
    return "static/enseignant.html"

@app.get("/etudiant", response_class=FileResponse, tags=["Pages Front-End"])
def student_page():
    return "static/etudiant.html"

@app.get("/lesson", response_class=FileResponse, tags=["Pages Front-End"])
def lesson_page():
    return "static/lesson.html"

@app.get("/certificate", response_class=FileResponse, tags=["Pages Front-End"])
def certificate_page():
    return "static/certificate.html"

@app.delete("/api/admin/delete_module/{module_id}")
async def delete_module(
    module_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user or current_user.role not in ["promoteur", "admin"]:
        raise HTTPException(status_code=403, detail="Accès interdit")

    module = db.execute(text("SELECT id FROM modules WHERE id = :id"), {"id": module_id}).fetchone()
    if not module:
        raise HTTPException(status_code=404, detail="Module introuvable")

    db.execute(text("DELETE FROM lessons WHERE course_id IN (SELECT id FROM courses WHERE module_id = :module_id)"), {"module_id": module_id})
    db.execute(text("DELETE FROM enrollments WHERE course_id IN (SELECT id FROM courses WHERE module_id = :module_id)"), {"module_id": module_id})
    db.execute(text("DELETE FROM courses WHERE module_id = :module_id"), {"module_id": module_id})
    db.execute(text("DELETE FROM modules WHERE id = :module_id"), {"module_id": module_id})
    db.commit()

    return {"success": True, "message": "Module et contenus associés supprimés avec succès"}

@app.delete("/api/enseignant/delete_course/{course_id}")
async def delete_course(
    course_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user or current_user.role != "enseignant":
        raise HTTPException(status_code=403, detail="Accès interdit")

    course = db.execute(
        text("SELECT id FROM courses WHERE id = :course_id AND teacher_id = :teacher_id"),
        {"course_id": course_id, "teacher_id": current_user.id},
    ).fetchone()
    if not course:
        raise HTTPException(status_code=404, detail="Cours introuvable ou non autorisé")

    db.execute(text("DELETE FROM lessons WHERE course_id = :course_id"), {"course_id": course_id})
    db.execute(text("DELETE FROM enrollments WHERE course_id = :course_id"), {"course_id": course_id})
    db.execute(text("DELETE FROM courses WHERE id = :course_id"), {"course_id": course_id})
    db.commit()

    return {"success": True, "message": "Cours supprimé"}

