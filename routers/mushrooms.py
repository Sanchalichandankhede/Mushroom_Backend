from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models, schemas
from auth_utils import get_current_user
from models import MushroomCategory

router = APIRouter()


@router.get("/", response_model=List[schemas.MushroomOut])
def list_mushrooms(
    skip: int = 0,
    limit: int = 20,
    category: Optional[MushroomCategory] = None,
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Mushroom)
    if category:
        query = query.filter(models.Mushroom.category == category)
    if search:
        query = query.filter(
            models.Mushroom.common_name.ilike(f"%{search}%") |
            models.Mushroom.scientific_name.ilike(f"%{search}%")
        )
    return query.offset(skip).limit(limit).all()


@router.get("/{mushroom_id}", response_model=schemas.MushroomOut)
def get_mushroom(mushroom_id: int, db: Session = Depends(get_db)):
    mushroom = db.query(models.Mushroom).filter(models.Mushroom.id == mushroom_id).first()
    if not mushroom:
        raise HTTPException(status_code=404, detail="Mushroom not found")
    return mushroom


@router.post("/", response_model=schemas.MushroomOut, status_code=201)
def create_mushroom(
    data: schemas.MushroomCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    mushroom = models.Mushroom(**data.model_dump())
    db.add(mushroom)
    db.commit()
    db.refresh(mushroom)
    return mushroom


@router.put("/{mushroom_id}", response_model=schemas.MushroomOut)
def update_mushroom(
    mushroom_id: int,
    data: schemas.MushroomCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    mushroom = db.query(models.Mushroom).filter(models.Mushroom.id == mushroom_id).first()
    if not mushroom:
        raise HTTPException(status_code=404, detail="Mushroom not found")
    for key, value in data.model_dump().items():
        setattr(mushroom, key, value)
    db.commit()
    db.refresh(mushroom)
    return mushroom


@router.delete("/{mushroom_id}", status_code=204)
def delete_mushroom(
    mushroom_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    mushroom = db.query(models.Mushroom).filter(models.Mushroom.id == mushroom_id).first()
    if not mushroom:
        raise HTTPException(status_code=404, detail="Mushroom not found")
    db.delete(mushroom)
    db.commit()


@router.get("/listings/all", response_model=List[schemas.ListingOut])
def list_all_listings(
    skip: int = 0,
    limit: int = 20,
    mushroom_id: Optional[int] = None,
    is_organic: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.MushroomListing).filter(models.MushroomListing.is_available == True)
    if mushroom_id:
        query = query.filter(models.MushroomListing.mushroom_id == mushroom_id)
    if is_organic is not None:
        query = query.filter(models.MushroomListing.is_organic == is_organic)
    return query.offset(skip).limit(limit).all()


@router.post("/listings/", response_model=schemas.ListingOut, status_code=201)
def create_listing(
    data: schemas.ListingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    mushroom = db.query(models.Mushroom).filter(models.Mushroom.id == data.mushroom_id).first()
    if not mushroom:
        raise HTTPException(status_code=404, detail="Mushroom not found")

    listing = models.MushroomListing(**data.model_dump(), seller_id=current_user.id)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.put("/listings/{listing_id}", response_model=schemas.ListingOut)
def update_listing(
    listing_id: int,
    data: schemas.ListingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    listing = db.query(models.MushroomListing).filter(
        models.MushroomListing.id == listing_id,
        models.MushroomListing.seller_id == current_user.id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or not yours")
    for key, value in data.model_dump().items():
        setattr(listing, key, value)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/listings/{listing_id}", status_code=204)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    listing = db.query(models.MushroomListing).filter(
        models.MushroomListing.id == listing_id,
        models.MushroomListing.seller_id == current_user.id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or not yours")
    db.delete(listing)
    db.commit()
