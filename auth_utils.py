from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import os

SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"

# Supabase Auth is handled on the client, we just verify the token here
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Supabase JWTs are signed with the project's JWT Secret
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="authenticated")
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        metadata = payload.get("user_metadata", {})
        
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    # If user doesn't exist in our 'public.users' table yet, create them
    if user is None:
        user = models.User(
            id=user_id,
            email=email,
            name=metadata.get("full_name", metadata.get("name", email.split('@')[0])),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    if not user.is_active:
        raise credentials_exception
    return user


def get_current_seller(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_seller:
        raise HTTPException(status_code=403, detail="Seller account required")
    return current_user
