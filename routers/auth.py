from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth_utils import get_current_user

router = APIRouter()


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Get the profile of the currently authenticated user.
    The user is automatically synced from Supabase to our local DB if they don't exist.
    """
    return current_user


@router.put("/me", response_model=schemas.UserOut)
def update_profile(
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Update profile fields like name or profile image.
    """
    allowed_fields = {"name", "profile_image"}
    for key, value in update_data.items():
        if key in allowed_fields:
            setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user
