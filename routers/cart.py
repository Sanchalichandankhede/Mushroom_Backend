from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth_utils import get_current_user

router = APIRouter()


@router.get("/", response_model=schemas.CartSummary)
def get_cart(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()

    total = sum(item.listing.price_per_kg * item.quantity_kg for item in items)
    return {
        "items": items,
        "total_items": len(items),
        "total_amount": round(total, 2)
    }


@router.post("/add", response_model=schemas.CartItemOut, status_code=201)
def add_to_cart(
    data: schemas.CartItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    listing = db.query(models.MushroomListing).filter(
        models.MushroomListing.id == data.listing_id,
        models.MushroomListing.is_available == True
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or unavailable")

    if data.quantity_kg > listing.quantity_kg:
        raise HTTPException(
            status_code=400,
            detail=f"Only {listing.quantity_kg} kg available"
        )

    # Check if already in cart
    existing = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.listing_id == data.listing_id
    ).first()

    if existing:
        existing.quantity_kg = data.quantity_kg
        db.commit()
        db.refresh(existing)
        return existing

    cart_item = models.CartItem(
        user_id=current_user.id,
        listing_id=data.listing_id,
        quantity_kg=data.quantity_kg
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item


@router.put("/{item_id}", response_model=schemas.CartItemOut)
def update_cart_item(
    item_id: int,
    quantity_kg: float,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if quantity_kg <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    item.quantity_kg = quantity_kg
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def remove_from_cart(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()


@router.delete("/clear/all", status_code=204)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).delete()
    db.commit()
