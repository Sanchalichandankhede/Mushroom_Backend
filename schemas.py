from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from models import MushroomCategory, OrderStatus


# ─── Auth Schemas ───────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    is_seller: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID | str
    name: str
    email: str
    is_seller: bool
    profile_image: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Mushroom Schemas ────────────────────────────────────────────────────────

class MushroomBase(BaseModel):
    common_name: str
    scientific_name: Optional[str] = None
    category: MushroomCategory = MushroomCategory.unknown
    description: Optional[str] = None
    habitat: Optional[str] = None
    season: Optional[str] = None
    image_url: Optional[str] = None
    edibility_notes: Optional[str] = None
    lookalikes: Optional[str] = None
    nutritional_info: Optional[str] = None


class MushroomCreate(MushroomBase):
    pass


class MushroomOut(MushroomBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Identification Schemas ──────────────────────────────────────────────────

class IdentificationResult(BaseModel):
    predicted_name: str
    confidence_score: float
    category: MushroomCategory
    is_safe: bool
    description: Optional[str]
    warnings: Optional[str]
    log_id: int
    image_url: Optional[str] = None
    toxicity_status: Optional[str] = None
    toxicity_details: Optional[str] = None
    health_metrics: Optional[str] = None
    recipes: Optional[List[str]] = None


# ─── Listing Schemas ─────────────────────────────────────────────────────────

class ListingCreate(BaseModel):
    mushroom_id: int
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    price_per_kg: float = Field(..., gt=0)
    quantity_kg: float = Field(..., gt=0)
    is_organic: bool = False
    image_url: Optional[str] = None
    location: Optional[str] = None


class ListingOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price_per_kg: float
    quantity_kg: float
    is_organic: bool
    is_available: bool
    image_url: Optional[str]
    location: Optional[str]
    created_at: datetime
    seller: UserOut
    mushroom: MushroomOut

    class Config:
        from_attributes = True


# ─── Cart Schemas ─────────────────────────────────────────────────────────────

class CartItemCreate(BaseModel):
    listing_id: int
    quantity_kg: float = Field(..., gt=0)


class CartItemOut(BaseModel):
    id: int
    quantity_kg: float
    added_at: datetime
    listing: ListingOut

    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    items: List[CartItemOut]
    total_items: int
    total_amount: float


# ─── Order Schemas ────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    delivery_address: str = Field(..., min_length=10)
    payment_method: Optional[str] = "cod"
    notes: Optional[str] = None


class OrderItemOut(BaseModel):
    id: int
    quantity_kg: float
    price_at_purchase: float
    listing: ListingOut

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    total_amount: float
    status: OrderStatus
    delivery_address: str
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


# ─── Notification Schemas ────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Home Page Content Schemas ───────────────────────────────────────────────

class ArticleOut(BaseModel):
    id: int
    title: str
    content: str
    image_url: Optional[str]
    author: str
    category: str
    is_trending: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QuickFactOut(BaseModel):
    id: int
    fact: str
    icon: str
    color_hex: str

    class Config:
        from_attributes = True


# ─── Chat Schemas ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str # 'user' or 'model'
    text: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime = Field(default_factory=datetime.now)
