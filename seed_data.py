# seed_data.py
from database import SessionLocal, engine
from models import User, Module, Course, Lesson, Question, Choice, Base
import bcrypt

def seed():
    db = SessionLocal()
    
    # Remplacement des rôles anglais par les rôles français attendus par tes routeurs
    password_bytes = "password".encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode("utf-8")
    teacher = User(username="prof_math", password_hash=hashed_password, role="enseignant")
    student = User(username="etudiant_test", password_hash=hashed_password, role="etudiant")
    db.add_all([teacher, student])
    db.commit()
    
    module = Module(title="Informatique Avancée", description="Apprentissage du développement web")
    db.add(module)
    db.commit()
    
    course = Course(title="Introduction à Python", content_tag="python_intro", module_id=module.id, teacher_id=teacher.id)
    db.add(course)
    db.commit()
    
    lesson = Lesson(title="Vidéo : Variables et Types", content_type="video", file_path="/uploads/videos/test.mp4", course_id=course.id)
    db.add(lesson)
    
    question = Question(text="Quelle est la fonction pour afficher quelque chose ?", tag="python_intro")
    db.add(question)
    db.commit()
    
    choices = [
        Choice(text="print()", is_correct=True, question_id=question.id),
        Choice(text="echo()", is_correct=False, question_id=question.id)
    ]
    db.add_all(choices)
    db.commit()
    
    print("✅ Base de données peuplée avec succès !")
    db.close()

if __name__ == "__main__":
    seed()