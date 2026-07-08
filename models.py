from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # 'admin', 'teacher', 'student'
    session_token_hash = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations pour la navigation transversale
    enrollments = relationship("Enrollment", back_populates="student")
    certificates = relationship("Certificate", back_populates="student")

class Module(Base):
    """ Dans 360Learning, c'est ce qu'on appelle un 'Parcours' ou 'Programme' """
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    courses = relationship("Course", back_populates="module")

class Course(Base):
    """ Représente un bloc de compétence spécifique (ex: Les bases de Python) """
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content_tag = Column(String, default="general") # Clé pour la banque de questions dynamique
    
    module_id = Column(Integer, ForeignKey("modules.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    
    module = relationship("Module", back_populates="courses")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")

class Lesson(Base):
    """ Contenu pédagogique (Vidéo, PDF). C'est ici qu'on valide les 70% """
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content_type = Column(String) # 'video', 'pdf'
    file_path = Column(String)
    
    course_id = Column(Integer, ForeignKey("courses.id"))
    course = relationship("Course", back_populates="lessons")

# ---- SYSTÈME D'ÉVALUATION (Approche Banque de Questions) ----

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    # quiz_id est supprimé car nous passons à une évaluation dynamique par 'tag'
    text = Column(String)
    tag = Column(String, default="general", index=True) # Indexé pour des recherches ultra-rapides
    
    choices = relationship("Choice", back_populates="question", cascade="all, delete-orphan")

class Choice(Base):
    __tablename__ = "choices"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    text = Column(String)
    is_correct = Column(Boolean, default=False)
    
    question = relationship("Question", back_populates="choices")

# ---- SYSTÈME DE SUIVI ET VALIDATION (Le cœur de ton prototype) ----

class Enrollment(Base):
    """ Moteur de progression 70/30 (SCORM-like) """
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    
    # La fameuse règle métier
    is_video_read = Column(Boolean, default=False) # Vaut 70 points
    quiz_score = Column(Float, default=0.0)        # Vaut 30 points
    progress = Column(Float, default=0.0)          # Total sur 100
    
    # Statut explicite pour faciliter les requêtes front-end
    status = Column(String, default="in_progress") # 'in_progress', 'completed'
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

class Certificate(Base):
    """ Preuve de complétion infalsifiable """
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True) # Optionnel : si on certifie tout le parcours
    
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("User", back_populates="certificates")