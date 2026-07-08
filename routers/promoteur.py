from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Module, Certificate, Course, Enrollment
from routers.auth import RequireRole
from schemas import ModuleCreate, ModuleResponse, IssueCertificate

router = APIRouter()


@router.post("/modules", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
def create_module(
    mod: ModuleCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["promoteur"]))
):
    """
    Permet au Promoteur de créer la structure macro-pédagogique (un Module / Parcours de formation).
    """
    new_mod = Module(title=mod.title, description=mod.description)
    db.add(new_mod)
    db.commit()
    db.refresh(new_mod)
    return new_mod


@router.get("/modules", response_model=List[ModuleResponse])
def list_modules(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["promoteur"]))
):
    """
    Permet au Promoteur d'obtenir la liste complète de tous les modules créés sur la plateforme.
    """
    mods = db.query(Module).all()
    return mods


@router.get("/students-progress")
def get_students_progress(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["promoteur"]))
):
    """
    Tableau de bord du Promoteur : Liste la progression de tous les étudiants.
    🚀 PERFORMANCE OPTIMISÉE (Anti-N+1) : Utilisation d'une jointure SQL explicite (JOIN) 
    permettant de tout récupérer en une seule et unique requête base de données.
    """
    # Une seule requête SQL combinée grâce aux jointures, indispensable pour monter en charge
    query_results = db.query(Enrollment, User, Course).\
        join(User, Enrollment.student_id == User.id).\
        join(Course, Enrollment.course_id == Course.id).\
        all()
        
    output = []
    for enrollment, student, course in query_results:
        # Vérification efficace de l'existence d'un certificat pour ce module précis
        cert_exists = db.query(Certificate).filter(
            Certificate.student_id == enrollment.student_id,
            Certificate.module_id == course.module_id
        ).first()
        
        output.append({
            "student_id": student.id,
            "student_name": student.username,
            "course_id": course.id,
            "course_title": course.title,
            "progress": enrollment.progress,
            "is_video_read": enrollment.is_video_read,
            "quiz_score": enrollment.quiz_score,
            "status": enrollment.status,
            "has_certificate": cert_exists is not None
        })
        
    return output


@router.post("/certificates", status_code=status.HTTP_201_CREATED)
def issue_certificate(
    payload: IssueCertificate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["promoteur"]))
):
    """
    Délivrance officielle et manuelle d'un certificat par le Promoteur.
    Sécurisé, typé via Pydantic et protégé contre les doublons.
    """
    # 1. Vérification de l'existence de l'étudiant
    student = db.query(User).filter(User.id == payload.student_id, User.role == "etudiant").first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="L'étudiant spécifié n'existe pas ou ne possède pas le bon rôle."
        )

    # 2. Vérification de la cible à certifier (Priorité au module/parcours complet, sinon au cours)
    if payload.module_id:
        target_module = db.query(Module).filter(Module.id == payload.module_id).first()
        if not target_module:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
            
        # Empêcher la double certification pour un même parcours
        existing_cert = db.query(Certificate).filter(
            Certificate.student_id == payload.student_id,
            Certificate.module_id == payload.module_id
        ).first()
    elif payload.course_id:
        target_course = db.query(Course).filter(Course.id == payload.course_id).first()
        if not target_course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
            
        existing_cert = db.query(Certificate).filter(
            Certificate.student_id == payload.student_id,
            Certificate.course_id == payload.course_id
        ).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous devez spécifier au moins un 'module_id' ou un 'course_id' pour émettre un certificat."
        )

    if existing_cert:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce certificat a déjà été officiellement délivré à cet étudiant."
        )

    # 3. Création et enregistrement du certificat
    new_certificate = Certificate(
        student_id=payload.student_id,
        module_id=payload.module_id,
        course_id=payload.course_id
    )
    db.add(new_certificate)
    db.commit()
    
    return {"msg": f"🎉 Certificat officiellement validé et délivré à l'étudiant '{student.username}' !"}