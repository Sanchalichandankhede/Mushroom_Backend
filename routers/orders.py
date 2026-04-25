from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models, schemas
from auth_utils import get_current_user
from models import OrderStatus

router = APIRouter()


@router.post("/place", response_model=schemas.OrderOut, status_code=201)
def place_order(
    data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    cart_items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Calculate total
    total = 0.0
    order_items_data = []

    for item in cart_items:
        listing = item.listing
        if not listing.is_available:
            raise HTTPException(
                status_code=400,
                detail=f"'{listing.title}' is no longer available"
            )
        if item.quantity_kg > listing.quantity_kg:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{listing.title}'"
            )
        line_total = listing.price_per_kg * item.quantity_kg
        total += line_total
        order_items_data.append({
            "listing_id": listing.id,
            "quantity_kg": item.quantity_kg,
            "price_at_purchase": listing.price_per_kg,
        })

    # Create order
    order = models.Order(
        user_id=current_user.id,
        total_amount=round(total, 2),
        delivery_address=data.delivery_address,
        payment_method=data.payment_method,
        notes=data.notes,
    )
    db.add(order)
    db.flush()  # get order.id before commit

    # Create order items + reduce listing stock
    for oi_data in order_items_data:
        order_item = models.OrderItem(order_id=order.id, **oi_data)
        db.add(order_item)

        # Deduct stock
        listing = db.query(models.MushroomListing).filter(
            models.MushroomListing.id == oi_data["listing_id"]
        ).first()
        listing.quantity_kg -= oi_data["quantity_kg"]
        if listing.quantity_kg <= 0:
            listing.is_available = False

    # Clear cart
    db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).delete()

    db.commit()
    db.refresh(order)
    return order


@router.get("/", response_model=List[schemas.OrderOut])
def get_my_orders(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    orders = db.query(models.Order).filter(
        models.Order.user_id == current_user.id
    ).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}/cancel", response_model=schemas.OrderOut)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.pending, OrderStatus.confirmed):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel an order with status '{order.status}'"
        )

    order.status = OrderStatus.cancelled

    # Restore stock
    for item in order.items:
        item.listing.quantity_kg += item.quantity_kg
        item.listing.is_available = True

    db.commit()
    db.refresh(order)
    return order


# Admin-only endpoint to update order status
@router.put("/{order_id}/status", response_model=schemas.OrderOut)
def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
