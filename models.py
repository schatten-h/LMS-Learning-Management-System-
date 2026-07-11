from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    email = Column(String, unique=True, index=True)
    role = Column(String) # 'promoteur', 'enseignant', 'etudiant'
    session_token_hash = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollments = relationship("Enrollment", back_populates="student")
    certificates = relationship("Certificate", back_populates="student")

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    courses = relationship("Course", back_populates="module")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content_tag = Column(String, default="general")
    
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    
    module = relationship("Module", back_populates="courses")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content_type = Column(String)
    file_path = Column(String)
    
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    course = relationship("Course", back_populates="lessons")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    tag = Column(String, default="general", index=True)
    
    choices = relationship("Choice", back_populates="question", cascade="all, delete-orphan")

class Choice(Base):
    __tablename__ = "choices"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    text = Column(String)
    is_correct = Column(Boolean, default=False)
    
    question = relationship("Question", back_populates="choices")

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    
    is_video_read = Column(Boolean, default=False)
    quiz_score = Column(Float, default=0.0)       
    progress = Column(Float, default=0.0)         
    
    status = Column(String, default="in_progress")
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True) 
    
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("User", back_populates="certificates")