from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import secrets
import hashlib
from database import get_db
from models import User
from schemas import UserCreate, UserLogin, UserResponse

router = APIRouter()

# Configuration du contexte de hachage pour les mots de passe (Bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Liste stricte des rôles imposés par le cahier des charges du professeur
ALLOWED_ROLES = ["etudiant", "enseignant", "promoteur"]


def hash_token(token: str) -> str:
    """
    Hache le jeton de session en SHA-256 avant stockage en base de données.
    Sécurité : Évite qu'un attaquant ayant accès à la BDD ne puisse voler les sessions actives.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dépendance globale pour récupérer l'utilisateur connecté via son cookie HTTP-Only.
    """
    raw_token = request.cookies.get("session_token")
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non autorisé : Aucune session active trouvée."
        )
    
    hashed = hash_token(raw_token)
    user = db.query(User).filter(User.session_token_hash == hashed).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expirée. Veuillez vous reconnecter."
        )
    return user


class RequireRole:
    """
    Contrôleur d'accès basé sur les rôles (RBAC).
    Permet de restreindre l'accès à une route aux rôles spécifiés.
    Exemple d'usage : Depends(RequireRole(["promoteur"]))
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Cette action requiert l'un des rôles suivants : {self.allowed_roles}"
            )
        return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Endpoint d'inscription.
    Vérifie la validité du rôle par rapport aux consignes (etudiant, enseignant, promoteur).
    """
    # Normalisation du rôle en minuscules pour éviter les erreurs de saisie (ex: "Etudiant" -> "etudiant")
    target_role = user.role.lower().strip()

    # 🔒 Validation stricte du rôle demandé
    if target_role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rôle invalide. Les rôles autorisés sont : {ALLOWED_ROLES}"
        )

    # 🔒 Sécurité : On bloque la création publique de comptes "promoteur" pour éviter l'élévation de privilèges
    if target_role == "promoteur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La création d'un compte Promoteur requiert une affectation directe par l'administrateur système."
        )

    # Vérification de l'unicité du nom d'utilisateur
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà utilisé."
        )

    # Hachage sécurisé du mot de passe
    hashed_password = pwd_context.hash(user.password)
    
    # Création et sauvegarde de l'utilisateur
    new_user = User(
        username=user.username,
        password_hash=hashed_password,
        role=target_role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login")
def login(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    """
    Endpoint de connexion.
    Génère un jeton de session sécurisé et l'envoie via un cookie HTTP-Only.
    """
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifiants ou mot de passe incorrects."
        )
    
    # Génération d'un token aléatoire sécurisé (64 caractères hexadécimaux)
    raw_token = secrets.token_hex(32)
    
    # Mise à jour du hash de session en BDD
    db_user.session_token_hash = hash_token(raw_token)
    db.commit()
    
    # Configuration sécurisée du cookie de session (Protection XSS et CSRF)
    response.set_cookie(
        key="session_token",
        value=raw_token,
        httponly=True,       # Bloque l'accès au cookie via document.cookie en JavaScript (Anti-XSS)
        max_age=86400,       # Durée de validité : 24 heures
        samesite="lax",      # Protection standard contre les attaques CSRF
        secure=False         # Passer à True uniquement lorsque le projet sera déployé en HTTPS
    )
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "role": db_user.role,
        "msg": "Connexion réussie."
    }


@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Endpoint de déconnexion.
    Invalide le token côté serveur et supprime le cookie côté client.
    """
    # Révocation du token en base de données
    current_user.session_token_hash = None
    db.commit()
    
    # Suppression du cookie dans le navigateur
    response.delete_cookie("session_token", samesite="lax")
    
    return {"msg": "Déconnexion réussie."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Endpoint de vérification de session (Profil de l'utilisateur connecté).
    Utile pour l'initialisation et la synchronisation des vues du Front-End.
    """
    return current_user