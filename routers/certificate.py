import os
from io import BytesIO
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session
from database import get_db
from models import User, Course, Enrollment, Module, Certificate
from routers.auth import RequireRole

router = APIRouter()


@router.get("/qr", tags=["Outils"])
def get_certificate_qr(student: str, course: str):
    """
    Générateur de flux QR Code brut (Utility).
    Permet de générer instantanément une image PNG de vérification.
    """
    payload = f"Vérification LMS | Étudiant: {student} | Contenu: {course} | Statut: Authentique"
    qr = qrcode.make(payload)
    
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.get("/course/{course_id}/get-certificate", tags=["Certificats"])
def download_certificate_by_course(
    course_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Génère et télécharge le certificat PDF officiel d'un cours spécifique.
    🔒 SÉCURITÉ : Vérifie la complétion effective via le statut 'termine' (Règle 70/30) 
    ou l'attribution manuelle par le Promoteur.
    """
    # 1. Vérifications de l'existence des entités
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")

    enrollment = db.query(Enrollment).filter_by(student_id=current_user.id, course_id=course_id).first()
    
    # Vérifier si le promoteur a délivré un certificat papier/numérique officiel pour ce cours
    promoter_cert = db.query(Certificate).filter_by(student_id=current_user.id, course_id=course_id).first()

    # Autorisation accordée si le cours est terminé à plus de 50% ou validé par le promoteur
    is_eligible = (enrollment and enrollment.status == "termine") or (promoter_cert is not None)

    if not is_eligible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Certificat indisponible. Vous devez valider le visionnage de la vidéo et réussir l'évaluation."
        )

    # 2. Configuration des chemins de fichiers
    os.makedirs("certificates", exist_ok=True)
    pdf_path = f"certificates/cert_course_{current_user.id}_{course_id}.pdf"
    qr_temp_path = f"certificates/qr_tmp_{current_user.id}_{course_id}.png"

    try:
        # 3. Génération du QR Code de sécurisation et d'authenticité
        qr_data = f"LMS Certificat Officiel\nID Étudiant: {current_user.id}\nNom: {current_user.username}\nCours: {course.title}"
        qr = qrcode.make(qr_data)
        qr.save(qr_temp_path)

        # 4. Dessin du Certificat PDF avec le moteur ReportLab
        c = canvas.Canvas(pdf_path)
        
        # Ligne d'encadrement esthétique (Style Diplôme)
        c.setLineWidth(4)
        c.rect(20, 20, 555, 802)
        
        # En-tête
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(297, 720, "CERTIFICAT DE RÉUSSITE")
        
        # Corps du document
        c.setFont("Helvetica", 14)
        c.drawCentredString(297, 640, "Le projet académique LMS certifie de manière authentique que :")
        
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(297, 590, f"{current_user.username.upper()}")
        
        c.setFont("Helvetica", 14)
        c.drawCentredString(297, 530, "a rempli avec succès toutes les exigences pédagogiques du cours :")
        
        c.setFont("Helvetica-Oblique", 16)
        c.drawCentredString(297, 480, f"« {course.title} »")
        
        # Affichage du score de progression de l'étudiant
        final_score = enrollment.progress if enrollment else 100.0
        c.setFont("Helvetica", 12)
        c.drawCentredString(297, 430, f"Moyenne globale acquise : {final_score:.2f}% (Validation 70/30)")

        # Intégration du QR Code de vérification en bas au centre
        c.drawImage(qr_temp_path, 247, 260, width=100, height=100)
        
        # Signature électronique simulée
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(297, 230, "Signé numériquement par le Promoteur")
        
        c.save()

    finally:
        # 5. Nettoyage du système de fichiers : on détruit le QR temporaire pour éviter d'encombrer le disque
        if os.path.exists(qr_temp_path):
            os.remove(qr_temp_path)

    return FileResponse(
        pdf_path, 
        media_type='application/pdf', 
        filename=f"Certificat_{course.title.replace(' ', '_')}.pdf"
    )


@router.get("/module/{module_id}/get-certificate", tags=["Certificats"])
def download_certificate_by_module(
    module_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(RequireRole(["etudiant"]))
):
    """
    Génère et télécharge le certificat global pour un Module entier (Parcours de plusieurs cours).
    Vérifie si le Promoteur a validé la certification globale de ce parcours.
    """
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module macro-pédagogique introuvable.")

    # Validation impérative par l'entité de contrôle (Le Promoteur)
    promoter_cert = db.query(Certificate).filter_by(student_id=current_user.id, module_id=module_id).first()
    if not promoter_cert:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Le certificat global de ce module n'a pas encore été visé ou délivré par le Promoteur."
        )

    os.makedirs("certificates", exist_ok=True)
    pdf_path = f"certificates/cert_module_{current_user.id}_{module_id}.pdf"
    qr_temp_path = f"certificates/qr_mod_tmp_{current_user.id}_{module_id}.png"

    try:
        qr = qrcode.make(f"Validation Parcours Complet\nModule: {module.title}\nBénéficiaire: {current_user.username}")
        qr.save(qr_temp_path)

        c = canvas.Canvas(pdf_path)
        c.setLineWidth(4)
        c.rect(20, 20, 555, 802)
        
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(297, 720, "DIPLÔME DE PARCOURS GLOBAL")
        
        c.setFont("Helvetica", 14)
        c.drawCentredString(297, 630, "Décerné solennellement à l'étudiant :")
        
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(297, 570, f"{current_user.username.upper()}")
        
        c.setFont("Helvetica", 14)
        c.drawCentredString(297, 500, f"Pour la validation complète de l'ensemble du module d'enseignement :")
        
        c.setFont("Helvetica-BoldOblique", 16)
        c.drawCentredString(297, 450, f"« {module.title} »")
        
        c.drawImage(qr_temp_path, 247, 240, width=100, height=100)
        
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(297, 200, "Validation et Certification émise par le Promoteur de l'établissement")
        c.save()
        
    finally:
        if os.path.exists(qr_temp_path):
            os.remove(qr_temp_path)

    return FileResponse(
        pdf_path, 
        media_type='application/pdf', 
        filename=f"Diplome_Module_{module.title.replace(' ', '_')}.pdf"
    )