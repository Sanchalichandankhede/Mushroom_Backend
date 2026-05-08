import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models

# Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Supabase Auth is handled on the client, we just verify the token here
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Cache for JWKS keys to avoid fetching on every request
_jwks_cache = None

async def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        try:
            jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                if response.status_code == 200:
                    _jwks_cache = response.json()
                else:
                    print(f"Warning: Could not fetch JWKS from {jwks_url}")
        except Exception as e:
            print(f"Error fetching JWKS: {e}")
    return _jwks_cache

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Get the unverified header to determine the algorithm
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        
        payload = None
        
        # 2. Strategy A: Verification using JWKS (Modern/Professional for ES256/RS256)
        if algorithm in ["ES256", "RS256"]:
            jwks = await get_jwks()
            if jwks:
                payload = jwt.decode(
                    token, 
                    jwks, 
                    algorithms=[algorithm], 
                    options={"verify_aud": False}
                )
        
        # 3. Strategy B: Fallback to HMAC Secret (HS256 - Legacy/Project Secret)
        if payload is None:
            if not SUPABASE_JWT_SECRET:
                print("CRITICAL: SUPABASE_JWT_SECRET is missing and JWKS strategy failed.")
                raise credentials_exception
            
            payload = jwt.decode(
                token, 
                SUPABASE_JWT_SECRET, 
                algorithms=["HS256"], 
                options={"verify_aud": False}
            )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        metadata = payload.get("user_metadata", {})
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError as e:
        print(f"JWT Error: {e}")
        print(f"Token header: {jwt.get_unverified_header(token)}")
        raise credentials_exception
    except Exception as e:
        print(f"Auth Exception: {e}")
        raise credentials_exception

    # Database sync/fetch logic
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
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
