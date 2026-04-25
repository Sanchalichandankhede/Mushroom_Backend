import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth_utils import get_current_user
from typing import Optional

router = APIRouter()

UPLOAD_DIR = "uploads/identifications"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def mock_ml_predict(image_path: str) -> dict:
    """
    Placeholder for your actual ML model inference.
    Replace this with a real model like:
      - TensorFlow/Keras CNN
      - PyTorch ResNet
      - HuggingFace image classifier
      - Google Vision API
    """
    return {
        "predicted_name": "Agaricus bisporus",
        "confidence_score": 0.92,
        "category": "edible",
        "is_safe": True,
        "description": "Common button mushroom, widely cultivated and eaten worldwide.",
        "warnings": None,
    }


@router.post("/upload", response_model=schemas.IdentificationResult)
async def identify_mushroom(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user)
):
    # Validate file extension
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Save uploaded image
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run ML model
    prediction = mock_ml_predict(filepath)

    # Try to find matching mushroom in DB
    mushroom = db.query(models.Mushroom).filter(
        models.Mushroom.common_name.ilike(f"%{prediction['predicted_name']}%") |
        models.Mushroom.scientific_name.ilike(f"%{prediction['predicted_name']}%")
    ).first()

    # Log the identification
    log = models.IdentificationLog(
        user_id=current_user.id if current_user else None,
        mushroom_id=mushroom.id if mushroom else None,
        uploaded_image_path=filepath,
        confidence_score=prediction["confidence_score"],
        predicted_name=prediction["predicted_name"],
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.IdentificationResult(
        **prediction,
        log_id=log.id
    )


@router.get("/history")
def get_identification_history(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    logs = db.query(models.IdentificationLog).filter(
        models.IdentificationLog.user_id == current_user.id
    ).order_by(models.IdentificationLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs


@router.put("/{log_id}/confirm")
def confirm_identification(
    log_id: int,
    mushroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    log = db.query(models.IdentificationLog).filter(
        models.IdentificationLog.id == log_id,
        models.IdentificationLog.user_id == current_user.id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Identification log not found")

    mushroom = db.query(models.Mushroom).filter(models.Mushroom.id == mushroom_id).first()
    if not mushroom:
        raise HTTPException(status_code=404, detail="Mushroom not found")

    log.mushroom_id = mushroom_id
    log.is_confirmed = True
    db.commit()
    return {"message": "Identification confirmed"}
