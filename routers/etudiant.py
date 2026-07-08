from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Module, Course, Lesson, Question, Choice, Enrollment, Certificate
from routers.auth import RequireRole
from schemas import SubmitQuiz, ProgressUpdate, EnrollmentResponse

router = APIRouter()

# =====================================================================
# SECTION 1 : DASHBOARD & CATALOGUE
# =====================================================================

@router.get("/dashboard")
def student_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Tableau de bord de l'étudiant : affiche ses cours suivis et ses certificats obtenus.
    🚀 PERFORMANCE : Optimisation des requêtes via des jointures explicites.
    """
    # Récupération optimisée des inscriptions avec les informations du cours associé
    enrollments = db.query(Enrollment, Course).\
        join(Course, Enrollment.course_id == Course.id).\
        filter(Enrollment.student_id == current_user.id).all()
        
    certs = db.query(Certificate, Module).\
        join(Module, Certificate.module_id == Module.id).\
        filter(Certificate.student_id == current_user.id).all()
    
    enr_data = [{
        "course_id": course.id, 
        "title": course.title, 
        "progress": enrollment.progress,
        "status": enrollment.status
    } for enrollment, course in enrollments]
    
    cert_data = [{
        "module_id": module.id,
        "module_title": module.title,
        "date_obtention": certificate.issue_date
    } for certificate, module in certs]
    
    return {"enrollments": enr_data, "certificates": cert_data}


@router.get("/catalog")
def get_catalog(
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Catalogue global : permet à l'étudiant de découvrir tous les cours disponibles sur le LMS.
    """
    courses = db.query(Course, Module).\
        join(Module, Course.module_id == Module.id).all()
        
    return [{
        "course_id": course.id,
        "course_title": course.title,
        "module_title": module.title,
        "content_tag": course.content_tag
    } for course, module in courses]


@router.post("/enroll/{course_id}", status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Inscrit l'étudiant à un cours spécifique et initialise son suivi de progression.
    """
    # Vérifier si le cours existe
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
        
    # Éviter les doublons d'inscription
    existing_enrollment = db.query(Enrollment).filter_by(student_id=current_user.id, course_id=course_id).first()
    if existing_enrollment:
        return {"msg": "Vous êtes déjà inscrit à ce cours.", "enrollment_id": existing_enrollment.id}
    
    new_enrollment = Enrollment(
        student_id=current_user.id, 
        course_id=course_id, 
        progress=0.0,
        is_video_read=False,
        quiz_score=0.0,
        status="en_cours"
    )
    db.add(new_enrollment)
    db.commit()
    return {"msg": "Inscription validée avec succès ! Vous pouvez commencer à apprendre."}


# =====================================================================
# SECTION 2 : ACCÈS AUX CONTENUS (LEÇONS & SYLLABUS)
# =====================================================================

@router.get("/courses/{course_id}/lessons")
def list_course_lessons(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Affiche le syllabus (leçons) d'un cours précis.
    🔒 SÉCURITÉ : L'étudiant doit impérativement être inscrit au cours pour voir les leçons.
    """
    enrollment = db.query(Enrollment).filter_by(student_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Accès refusé. Vous devez d'abord vous inscrire à ce cours."
        )
        
    lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
    return [{
        "id": lesson.id, 
        "title": lesson.title, 
        "content_type": lesson.content_type, 
        "file_path": lesson.file_path
    } for lesson in lessons]


# =====================================================================
# SECTION 3 : MOTEUR D'ÉVALUATION DYNAMIQUE PAR TAGS & NOTATION 70/30
# =====================================================================

@router.get("/courses/{course_id}/quiz")
def get_dynamic_quiz(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Génère un quiz dynamique à la volée. 
    Va chercher toutes les questions de la banque de questions qui possèdent le même tag que le cours.
    🔒 SÉCURITÉ : Masque le champ 'is_correct' pour empêcher la triche via l'inspecteur du navigateur.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
        
    # Extraction dynamique des questions via le tag du cours (Concept 360Learning)
    questions = db.query(Question).filter(Question.tag == course.content_tag).all()
    
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Aucune évaluation n'est disponible pour ce cours actuellement."
        )
        
    return [{
        "question_id": q.id, 
        "text": q.text, 
        "choices": [{"id": c.id, "text": c.text} for c in q.choices] # 'is_correct' est filtré ici !
    } for q in questions]


@router.post("/courses/submit-quiz")
def submit_quiz_answers(
    payload: SubmitQuiz, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Soumission et correction automatique du quiz d'un cours.
    Calcule le score et met à jour instantanément la progression globale via la règle des 70/30.
    """
    enrollment = db.query(Enrollment).filter_by(student_id=current_user.id, course_id=payload.course_id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscription à ce cours introuvable.")
        
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    
    # 1. Récupération des questions officielles pour valider la correction
    questions = db.query(Question).filter(Question.tag == course.content_tag).all()
    total_questions = len(questions)
    
    if total_questions == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce cours ne possède pas de questions associées.")

    correct_count = 0
    
    # 2. Algorithme de correction sécurisé (Vérification côté serveur)
    for user_answer in payload.answers:
        choice = db.query(Choice).filter(
            Choice.id == user_answer.choice_id, 
            # Garantit que la réponse appartient à la bonne question
            Choice.question_id == user_answer.question_id 
        ).first()
        
        if choice and choice.is_correct:
            correct_count += 1
            
    # Calcul de la note du quiz ramenée sur 100
    quiz_percentage = (correct_count / total_questions) * 100
    enrollment.quiz_score = quiz_percentage

    # 3. 🧮 APPLICATION DU MOTEUR DE NOTATION PROFESSIONNEL 70% / 30%
    video_weight = 70.0 if enrollment.is_video_read else 0.0
    quiz_weight = (enrollment.quiz_score / 100.0) * 30.0
    
    enrollment.progress = video_weight + quiz_weight
    
    # Mise à jour du statut si le parcours est complété avec succès (note globale >= 50%)
    if enrollment.progress >= 50.0 and enrollment.is_video_read:
        enrollment.status = "termine"
        
    db.commit()
    
    return {
        "quiz_score_pure": f"{quiz_percentage:.2f}%",
        "points_quiz_obtenus": f"{quiz_weight:.2f} / 30",
        "progression_globale_cours": f"{enrollment.progress:.2f} / 100",
        "status": enrollment.status
    }


@router.post("/courses/{course_id}/track-video")
def track_video_completion(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Valide le visionnage complet des vidéos pédagogiques du cours.
    Déclenche automatiquement le recalcul de la progression globale (Apporte instantanément 70 points).
    """
    enrollment = db.query(Enrollment).filter_by(student_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inscription à ce cours introuvable.")
        
    # Passage de l'état vidéo à Lu
    enrollment.is_video_read = True
    
    # 🧮 RECALCUL DU MOTEUR 70/30
    video_weight = 70.0  # Désormais acquis
    quiz_weight = (enrollment.quiz_score / 100.0) * 30.0
    
    enrollment.progress = video_weight + quiz_weight
    
    db.commit()
    
    return {
        "msg": "Visionnage vidéo enregistré avec succès (+70 points d'assiduité).",
        "progression_globale_cours": f"{enrollment.progress:.2f} / 100"
    }