from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class MushroomCategory(str, enum.Enum):
    edible = "edible"
    poisonous = "poisonous"
    medicinal = "medicinal"
    unknown = "unknown"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    # Changed to String/UUID to match Supabase Auth ID
    id = Column(String(100), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    # password is not needed if using Supabase Auth, but we can keep it for flexibility
    hashed_password = Column(String(255), nullable=True) 
    profile_image = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_seller = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    identifications = relationship("IdentificationLog", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="user")
    listings = relationship("MushroomListing", back_populates="seller")


class Mushroom(Base):
    __tablename__ = "mushrooms"

    id = Column(Integer, primary_key=True, index=True)
    common_name = Column(String(150), nullable=False, index=True)
    scientific_name = Column(String(200), nullable=True)
    category = Column(Enum(MushroomCategory), default=MushroomCategory.unknown)
    description = Column(Text, nullable=True)
    habitat = Column(String(255), nullable=True)
    season = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    edibility_notes = Column(Text, nullable=True)
    lookalikes = Column(Text, nullable=True)  # JSON string of lookalike names
    nutritional_info = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    identifications = relationship("IdentificationLog", back_populates="mushroom")
    listings = relationship("MushroomListing", back_populates="mushroom")


class IdentificationLog(Base):
    __tablename__ = "identification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), ForeignKey("users.id"), nullable=True)
    mushroom_id = Column(Integer, ForeignKey("mushrooms.id"), nullable=True)
    uploaded_image_path = Column(String(500), nullable=False)
    confidence_score = Column(Float, nullable=True)
    predicted_name = Column(String(200), nullable=True)
    is_confirmed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="identifications")
    mushroom = relationship("Mushroom", back_populates="identifications")


class MushroomListing(Base):
    __tablename__ = "mushroom_listings"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(String(100), ForeignKey("users.id"), nullable=False)
    mushroom_id = Column(Integer, ForeignKey("mushrooms.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price_per_kg = Column(Float, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    is_organic = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    image_url = Column(String(500), nullable=True)
    location = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    seller = relationship("User", back_populates="listings")
    mushroom = relationship("Mushroom", back_populates="listings")
    cart_items = relationship("CartItem", back_populates="listing")
    order_items = relationship("OrderItem", back_populates="listing")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("mushroom_listings.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False, default=1.0)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="cart_items")
    listing = relationship("MushroomListing", back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending)
    delivery_address = Column(Text, nullable=False)
    payment_method = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("mushroom_listings.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    price_at_purchase = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    listing = relationship("MushroomListing", back_populates="order_items")
