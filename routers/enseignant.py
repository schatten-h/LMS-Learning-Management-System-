import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, Module, Course, Lesson, Question, Choice
from routers.auth import RequireRole, get_current_user  # Import de la sécurité
from schemas import (
    CourseCreate, 
    CourseResponse, 
    ModuleResponse, 
    QuestionCreate, 
    QuestionResponse, 
    BankQuestionsPayload  # Import du schéma en lot
)

# Configuration globale unique du routeur
router = APIRouter(
    prefix="/api/enseignant",
    tags=["Enseignant"]
)


@router.get("/modules", response_model=List[ModuleResponse])
def enseignant_list_modules(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["enseignant"]))
):
    """
    Permet à l'enseignant de consulter les modules structurels créés par le Promoteur 
    afin de savoir où il peut rattacher ses nouveaux cours.
    """
    modules = db.query(Module).all()
    return modules


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course: CourseCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["enseignant"]))
):
    """
    Permet à l'enseignant de créer un nouveau cours rattaché à un module global.
    Chaque cours embarque un 'content_tag' pour cibler dynamiquement les évaluations correspondantes.
    """
    module_exists = db.query(Module).filter(Module.id == course.module_id).first()
    if not module_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Le module global spécifié n'existe pas. Veuillez contacter le Promoteur."
        )
    
    new_course = Course(
        title=course.title, 
        module_id=course.module_id, 
        teacher_id=current_user.id,
        content_tag=course.content_tag.lower().strip()
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.get("/courses", response_model=List[CourseResponse])
def enseignant_list_courses(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["enseignant"]))
):
    """
    Liste l'ensemble des cours créés exclusivement par l'enseignant connecté.
    """
    courses = db.query(Course).filter(Course.teacher_id == current_user.id).all()
    return courses


@router.post("/lessons", status_code=status.HTTP_201_CREATED)
def upload_lesson(
    title: str = Form(...),
    course_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole(["enseignant"]))
):
    """
    Endpoint d'upload de médias (PDF ou vidéo MP4) avec validation de propriété.
    """
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == current_user.id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Cours introuvable ou vous n'avez pas les droits d'édition sur ce contenu."
        )

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext == '.pdf':
        subfolder = "pdfs"
        content_type = "pdf"
    elif file_ext == '.mp4':
        subfolder = "videos"
        content_type = "video"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Format de fichier refusé. Seuls les documents PDF et les vidéos MP4 sont autorisés."
        )

    filename = f"{uuid.uuid4()}{file_ext}"
    relative_path = f"/uploads/{subfolder}/{filename}"
    absolute_path = os.path.join("uploads", subfolder, filename)

    with open(absolute_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_lesson = Lesson(
        title=title, 
        content_type=content_type, 
        file_path=relative_path, 
        course_id=course_id
    )
    db.add(new_lesson)
    db.commit()
    
    return {"msg": "Leçon multimédia ajoutée et liée avec succès.", "lesson_id": new_lesson.id}


@router.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question_data: QuestionCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["enseignant"]))
):
    """
    Crée une question unique avec ses choix.
    """
    new_question = Question(
        text=question_data.text,
        tag=question_data.tag.lower().strip()
    )
    db.add(new_question)
    db.flush()
    
    for choice in question_data.choices:
        new_choice = Choice(
            question_id=new_question.id, 
            text=choice.text, 
            is_correct=choice.is_correct
        )
        db.add(new_choice)
            
    db.commit()
    db.refresh(new_question)
    return new_question


@router.post("/questions/bank", status_code=status.HTTP_201_CREATED)
def add_questions_to_bank(
    payload: BankQuestionsPayload, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Réceptionne le payload du formulaire JavaScript pour insérer un bloc 
    de questions associées à un tag unique dans la banque de données.
    """
    # Vérification stricte des permissions
    if current_user.role not in ["enseignant", "promoteur"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Action réservée aux enseignants et promoteurs."
        )

    if not payload.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="La liste de questions ne peut pas être vide."
        )

    try:
        norm_tag = payload.tag.lower().strip()
        
        for q_data in payload.questions:
            # 1. Insertion de la question
            new_question = Question(
                text=q_data.text,
                tag=norm_tag
                # teacher_id=current_user.id  <-- À décommenter uniquement si la colonne existe dans ton modèle Question
            )
            db.add(new_question)
            db.flush()

            # 2. Insertion des choix associés
            for c_data in q_data.choices:
                new_choice = Choice(
                    text=c_data.text,
                    is_correct=c_data.is_correct,
                    question_id=new_question.id
                )
                db.add(new_choice)

        db.commit()
        return {"message": "Questions ajoutées avec succès à la banque de données !"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement dans Neon : {str(e)}"
        )