from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# SECTION 1 : BANQUE DE QUESTIONS DYNAMIQUE

class ChoiceBase(BaseModel):
    text: str

class ChoiceCreate(ChoiceBase):
    is_correct: bool = False

class ChoiceResponse(ChoiceBase):
    id: int
    # model_config permet à Pydantic de lire directement les objets SQLAlchemy ORM
    model_config = ConfigDict(from_attributes=True)

class QuestionCreate(BaseModel):
    text: str
    tag: str = "general" # Permet au professeur de catégoriser la question
    choices: List[ChoiceCreate]

class QuestionResponse(BaseModel):
    id: int
    text: str
    tag: str
    choices: List[ChoiceResponse] # Filtré : 'is_correct' n'est pas envoyé au front-end !
    model_config = ConfigDict(from_attributes=True)

# 1. Structure d'un choix dans une question
class ChoiceCreate(BaseModel):
    text: str
    is_correct: bool

# 2. Structure d'une question individuelle
class QuestionCreate(BaseModel):
    text: str
    choices: List[ChoiceCreate]

# 3. Structure du payload principal reçu par l'API
class BankQuestionsPayload(BaseModel):
    tag: str
    questions: List[QuestionCreate]


# =====================================================================
# SECTION 2 : ÉVALUATIONS & SOUMISSIONS (Moteur 30%)
# =====================================================================

class SubmitAnswer(BaseModel):
    question_id: int
    choice_id: int

class SubmitQuiz(BaseModel):
    course_id: int # Crucial : lie directement la soumission au parcours de l'étudiant
    answers: List[SubmitAnswer]


# =====================================================================
# SECTION 3 : AUTHENTIFICATION & UTILISATEURS
# =====================================================================

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "student" # 'admin', 'teacher', 'student'

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# SECTION 4 : ARCHITECTURE APPRENTISSAGE (360Learning-like)
# =====================================================================

class ModuleCreate(BaseModel):
    title: str
    description: str

class ModuleResponse(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CourseCreate(BaseModel):
    title: str
    module_id: int
    content_tag: str = "general"

class CourseResponse(BaseModel):
    id: int
    title: str
    content_tag: str
    module_id: int
    teacher_id: int
    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# SECTION 5 : SUIVI DE PROGRESSION & CERTIFICATS (Moteur 70%)
# =====================================================================

class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    is_video_read: bool
    quiz_score: float
    progress: float
    status: str
    enrolled_at: datetime
    model_config = ConfigDict(from_attributes=True)

class IssueCertificate(BaseModel):
    student_id: int
    course_id: Optional[int] = None
    module_id: Optional[int] = None

class ProgressUpdate(BaseModel):
    is_read: bool
    score: float