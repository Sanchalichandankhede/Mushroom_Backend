import os
import uuid
import shutil
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth_utils import get_current_user
from cloudinary_utils import upload_image_stream
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

UPLOAD_DIR = "uploads/identifications"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# ── Lazy-loaded TensorFlow model ─────────────────────────────────────────────
_model = None
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "mushroom_prediction_model.keras")

# Common mushroom class names — update this list to match your training dataset
CLASS_NAMES = [
    "Agaricus bisporus",       # Button Mushroom
    "Amanita muscaria",        # Fly Agaric (toxic)
    "Amanita phalloides",      # Death Cap (deadly)
    "Boletus edulis",          # Porcini / King Bolete
    "Cantharellus cibarius",   # Chanterelle
    "Coprinus comatus",        # Shaggy Ink Cap
    "Ganoderma lucidum",       # Reishi (medicinal)
    "Grifola frondosa",        # Maitake / Hen of the Woods
    "Hericium erinaceus",      # Lion's Mane
    "Lactarius deliciosus",    # Saffron Milk Cap
    "Lentinula edodes",        # Shiitake
    "Morchella esculenta",     # Morel
    "Pleurotus ostreatus",     # Oyster Mushroom
    "Psilocybe cubensis",      # Magic Mushroom (psychoactive)
    "Russula emetica",         # The Sickener (toxic)
    "Trametes versicolor",     # Turkey Tail (medicinal)
    "Tricholoma matsutake",    # Matsutake
    "Tuber melanosporum",      # Black Truffle
    "Volvariella volvacea",    # Paddy Straw Mushroom
]

# Safety lookup — simple mapping based on known species
SAFETY_MAP = {
    "Agaricus bisporus":     {"category": "edible",    "is_safe": True},
    "Amanita muscaria":      {"category": "poisonous", "is_safe": False},
    "Amanita phalloides":    {"category": "poisonous", "is_safe": False},
    "Boletus edulis":        {"category": "edible",    "is_safe": True},
    "Cantharellus cibarius": {"category": "edible",    "is_safe": True},
    "Coprinus comatus":      {"category": "edible",    "is_safe": True},
    "Ganoderma lucidum":     {"category": "medicinal", "is_safe": True},
    "Grifola frondosa":      {"category": "edible",    "is_safe": True},
    "Hericium erinaceus":    {"category": "medicinal", "is_safe": True},
    "Lactarius deliciosus":  {"category": "edible",    "is_safe": True},
    "Lentinula edodes":      {"category": "edible",    "is_safe": True},
    "Morchella esculenta":   {"category": "edible",    "is_safe": True},
    "Pleurotus ostreatus":   {"category": "edible",    "is_safe": True},
    "Psilocybe cubensis":    {"category": "poisonous", "is_safe": False},
    "Russula emetica":       {"category": "poisonous", "is_safe": False},
    "Trametes versicolor":   {"category": "medicinal", "is_safe": True},
    "Tricholoma matsutake":  {"category": "edible",    "is_safe": True},
    "Tuber melanosporum":    {"category": "edible",    "is_safe": True},
    "Volvariella volvacea":  {"category": "edible",    "is_safe": True},
}


def get_model():
    """Lazy-load the Keras model on first call."""
    global _model
    if _model is None:
        try:
            import tensorflow as tf
            print(f"Loading Keras model from: {MODEL_PATH}")
            _model = tf.keras.models.load_model(MODEL_PATH)
            print("Model loaded successfully!")
            print(f"  Input shape : {_model.input_shape}")
            print(f"  Output shape: {_model.output_shape}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise HTTPException(status_code=503, detail=f"ML model could not be loaded: {e}")
    return _model


def preprocess_image(image_path: str, target_size=(224, 224)):
    """Load an image, resize it, and normalise pixel values for the CNN."""
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    img = img.resize(target_size)
    img_array = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(img_array, axis=0)  # add batch dim


def predict_mushroom(image_path: str) -> dict:
    """Run the Keras model and return prediction dict."""
    model = get_model()

    # Determine input size from model
    input_shape = model.input_shape  # e.g. (None, 224, 224, 3)
    h, w = input_shape[1], input_shape[2]
    target_size = (h or 224, w or 224)

    img = preprocess_image(image_path, target_size)
    predictions = model.predict(img, verbose=0)

    # Handle the output
    num_classes = predictions.shape[-1]
    class_idx = int(np.argmax(predictions[0]))
    confidence = float(predictions[0][class_idx])

    # Map index to name
    if class_idx < len(CLASS_NAMES):
        predicted_name = CLASS_NAMES[class_idx]
    else:
        predicted_name = f"Unknown Species (class {class_idx})"

    safety = SAFETY_MAP.get(predicted_name, {"category": "unknown", "is_safe": False})

    return {
        "predicted_name": predicted_name,
        "confidence_score": round(confidence, 4),
        "category": safety["category"],
        "is_safe": safety["is_safe"],
    }


# ── Gemini helper ────────────────────────────────────────────────────────────
def _get_gemini_client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)


async def get_gemini_analysis(predicted_name: str, category: str, image_path: Optional[str] = None) -> dict:
    """Ask Gemini for species verification, toxicity info, health metrics, and recipes using the scanned image."""
    client = _get_gemini_client()
    if client is None:
        return {
            "predicted_name": predicted_name,
            "toxicity_status": category.title(),
            "toxicity_details": "Gemini API not configured.",
            "health_metrics": "Not available.",
            "recipes": [],
        }

    from google.genai import types
    from PIL import Image

    contents = []
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            contents.append(img)
        except Exception as e:
            print(f"Failed to load image for Gemini analysis: {e}")

    prompt = (
        f"Analyze the mushroom shown in this image. "
        f"A CNN classifier predicted this mushroom might be '{predicted_name}' (category: {category}). "
        "Please inspect the image carefully to identify the mushroom species. If the CNN prediction is incorrect, "
        "or if the name is too generic/unknown, please correct it to the actual species name. "
        "Provide the following fields in clean, plain text (NO Markdown, NO asterisks, NO hashtags, NO dashes as separators):\n\n"
        "1. PREDICTED NAME: The corrected common or scientific name of this mushroom species (max 3 words).\n"
        "2. TOXICITY STATUS: One word — Edible, Toxic, Psychoactive, or Medicinal.\n"
        "3. TOXICITY DETAILS: A short 2-3 sentence paragraph about its safety profile.\n"
        "4. HEALTH METRICS: A short 2-3 sentence paragraph about its nutritional and health benefits.\n"
        "5. RECIPES: Exactly 2 very short recipes (3-4 sentences each) for culinary mushrooms, OR safety/handling preparation steps if the mushroom is toxic/psychoactive. Separate recipes with the delimiter |||.\n\n"
        "Format your response EXACTLY like this (including the labels):\n"
        "PREDICTED NAME: ...\n"
        "TOXICITY STATUS: ...\n"
        "TOXICITY DETAILS: ...\n"
        "HEALTH METRICS: ...\n"
        "RECIPES: Recipe 1 text ||| Recipe 2 text"
    )
    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            config=types.GenerateContentConfig(
                temperature=0.5,
            ),
            contents=contents,
        )

        text = response.text.strip()
        return _parse_gemini_response(text, predicted_name, category)

    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return {
            "predicted_name": predicted_name,
            "toxicity_status": category.title(),
            "toxicity_details": f"Could not fetch details: {e}",
            "health_metrics": "Not available.",
            "recipes": [],
        }


def _parse_gemini_response(text: str, default_name: str, fallback_category: str) -> dict:
    """Parse the structured Gemini response into a dict."""
    result = {
        "predicted_name": default_name,
        "toxicity_status": fallback_category.title(),
        "toxicity_details": "",
        "health_metrics": "",
        "recipes": [],
    }

    lines = text.split("\n")
    current_key = None
    buffer = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if line_stripped.upper().startswith("PREDICTED NAME:"):
            if current_key and buffer:
                result[current_key] = " ".join(buffer).strip()
            current_key = "predicted_name"
            buffer = [line_stripped.split(":", 1)[1].strip()]
        elif line_stripped.upper().startswith("TOXICITY STATUS:"):
            if current_key and buffer:
                result[current_key] = " ".join(buffer).strip()
            current_key = "toxicity_status"
            buffer = [line_stripped.split(":", 1)[1].strip()]
        elif line_stripped.upper().startswith("TOXICITY DETAILS:"):
            if current_key and buffer:
                result[current_key] = " ".join(buffer).strip()
            current_key = "toxicity_details"
            buffer = [line_stripped.split(":", 1)[1].strip()]
        elif line_stripped.upper().startswith("HEALTH METRICS:"):
            if current_key and buffer:
                result[current_key] = " ".join(buffer).strip()
            current_key = "health_metrics"
            buffer = [line_stripped.split(":", 1)[1].strip()]
        elif line_stripped.upper().startswith("RECIPES:"):
            if current_key and buffer:
                result[current_key] = " ".join(buffer).strip()
            current_key = "recipes"
            buffer = [line_stripped.split(":", 1)[1].strip()]
        else:
            buffer.append(line_stripped)

    # Flush the last key
    if current_key and buffer:
        value = " ".join(buffer).strip()
        if current_key == "recipes":
            result["recipes"] = [r.strip() for r in value.split("|||") if r.strip()]
        else:
            result[current_key] = value

    # Clean markdown from all text fields
    for key in ["predicted_name", "toxicity_status", "toxicity_details", "health_metrics"]:
        val = result.get(key, "")
        if isinstance(val, str):
            val = val.replace("**", "").replace("*", "").replace("###", "").replace("##", "").replace("#", "").replace("---", "")
            result[key] = val.strip()

    result["recipes"] = [
        r.replace("**", "").replace("*", "").replace("#", "").replace("---", "").strip()
        for r in result.get("recipes", [])
    ]

    return result


# ── API Endpoints ────────────────────────────────────────────────────────────

@router.post("/upload", response_model=schemas.IdentificationResult)
async def identify_mushroom(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user)
):
    # Validate file extension
    ext = os.path.splitext(file.filename or "image.jpg")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Save uploaded image locally (temporary)
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Upload to Cloudinary
    cloudinary_url = ""
    try:
        cloudinary_url = upload_image_stream(open(filepath, "rb"), folder="mushroom_scans") or ""
    except Exception as e:
        print(f"Cloudinary upload failed (non-fatal): {e}")

    # 2. Run the Keras ML model
    try:
        prediction = predict_mushroom(filepath)
    except HTTPException:
        raise
    except Exception as e:
        print(f"ML Prediction Error: {e}")
        # Fallback to a safe default
        prediction = {
            "predicted_name": "Unknown Mushroom",
            "confidence_score": 0.0,
            "category": "unknown",
            "is_safe": False,
        }

    # 3. Get Gemini analysis (multimodal species check + toxicity + recipes)
    gemini_data = await get_gemini_analysis(prediction["predicted_name"], prediction["category"], filepath)

    # Use corrected name and safety details from Gemini
    final_predicted_name = gemini_data.get("predicted_name") or prediction["predicted_name"]
    final_predicted_name = final_predicted_name.strip()

    # Align safety indicators based on Gemini response
    gemini_tox = gemini_data.get("toxicity_status", "").lower()
    is_safe = prediction["is_safe"]
    category = prediction["category"]

    if "toxic" in gemini_tox or "poisonous" in gemini_tox or "psychoactive" in gemini_tox:
        is_safe = False
        category = "poisonous"
    elif "edible" in gemini_tox:
        is_safe = True
        category = "edible"
    elif "medicinal" in gemini_tox:
        is_safe = True
        category = "medicinal"

    # 4. Try to find matching mushroom in DB
    mushroom = db.query(models.Mushroom).filter(
        models.Mushroom.common_name.ilike(f"%{final_predicted_name}%") |
        models.Mushroom.scientific_name.ilike(f"%{final_predicted_name}%")
    ).first()

    # 5. Log to database
    image_to_store = cloudinary_url if cloudinary_url else filepath
    log = models.IdentificationLog(
        user_id=current_user.id if current_user else None,
        mushroom_id=mushroom.id if mushroom else None,
        uploaded_image_path=image_to_store,
        confidence_score=prediction["confidence_score"],
        predicted_name=final_predicted_name,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # 6. Build description & warnings
    description = gemini_data.get("toxicity_details", "")
    warnings = None
    if not is_safe:
        warnings = "WARNING: This mushroom may be toxic or dangerous. Do NOT consume it without expert verification."

    return schemas.IdentificationResult(
        predicted_name=final_predicted_name,
        confidence_score=prediction["confidence_score"],
        category=category,
        is_safe=is_safe,
        description=description,
        warnings=warnings,
        log_id=log.id,
        image_url=cloudinary_url or None,
        toxicity_status=gemini_data.get("toxicity_status", category.title()),
        toxicity_details=gemini_data.get("toxicity_details", ""),
        health_metrics=gemini_data.get("health_metrics", ""),
        recipes=gemini_data.get("recipes", []),
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
