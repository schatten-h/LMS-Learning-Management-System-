from database import SessionLocal, engine
from models import User, Module, Course, Lesson, Question, Choice, Base
from passlib.context import CryptContext

# Configuration du mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    db = SessionLocal()
    
    # 1. Création des utilisateurs de test
    teacher = User(username="prof_math", password_hash=pwd_context.hash("password"), role="teacher")
    student = User(username="etudiant_test", password_hash=pwd_context.hash("password"), role="student")
    db.add_all([teacher, student])
    db.commit()
    
    # 2. Création d'un module et d'un cours avec le fameux "tag"
    module = Module(title="Informatique Avancée", description="Apprentissage du développement web")
    db.add(module)
    db.commit()
    
    course = Course(title="Introduction à Python", content_tag="python_intro", module_id=module.id, teacher_id=teacher.id)
    db.add(course)
    db.commit()
    
    # 3. Ajout d'une leçon liée au cours
    lesson = Lesson(title="Vidéo : Variables et Types", content_type="video", file_path="/uploads/videos/test.mp4", course_id=course.id)
    db.add(lesson)
    
    # 4. Ajout de questions avec le même tag ("python_intro")
    question = Question(text="Quelle est la fonction pour afficher quelque chose ?", tag="python_intro")
    db.add(question)
    db.commit()
    
    # 5. Ajout des choix
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