# 🎓 Plateforme LMS (Learning Management System)

Une application web moderne de gestion de l'apprentissage (style 360Learning) développée avec **FastAPI**, **SQLAlchemy** et **Neon (PostgreSQL)**.

## 🚀 Fonctionnalités principales
- **Espace Promoteur** : Création de cohortes/modules et inscriptions manuelles.
- **Espace Enseignant** : Création de cours par Tag, upload de médias (PDF/MP4) et alimentation d'une banque de questions dynamiques.
- **Moteur d'Évaluation (30%) & Progression (70%)** : Suivi des étudiants et génération automatique de certificats.

## 🛠️ Installation en Local

### 1. Prérequis
Assurez-vous d'avoir Python 3.10+ installé.

### 2. Cloner le projet & installer les dépendances
```bash
git clone <URL_DE_TON_DEPOT_GITHUB>
cd lms
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
`

### 3. Variables d'environnement
Créez un fichier `.env` à la racine du projet et ajoutez vos identifiants de base de données Neon :
```env
PGUSER=votre_utilisateur
PGPASSWORD=votre_mot_de_passe
PGHOST=votre_hote_neon
PGDATABASE=neondb
`
uvicorn main:app --reload