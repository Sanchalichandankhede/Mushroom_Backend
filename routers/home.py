from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from typing import List
import random

router = APIRouter()

@router.get("/quick-facts", response_model=List[schemas.QuickFactOut])
def get_quick_facts(db: Session = Depends(get_db)):
    facts = db.query(models.QuickFact).all()
    if not facts:
        return [
            {"id": 1, "fact": "Mushrooms are more closely related to humans than plants.", "icon": "Zap", "color_hex": "#FFD700"},
            {"id": 2, "fact": "The largest organism on Earth is a honey fungus.", "icon": "Globe", "color_hex": "#4CAF50"},
            {"id": 3, "fact": "Some mushrooms can glow in the dark.", "icon": "Lightbulb", "color_hex": "#00BCD4"},
            {"id": 4, "fact": "Mushrooms can be used to create sustainable leather.", "icon": "Shield", "color_hex": "#2196F3"},
        ]
    return random.sample(facts, min(len(facts), 5))

@router.get("/articles", response_model=List[schemas.ArticleOut])
def get_articles(category: str = None, trending: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Article)
    if category:
        query = query.filter(models.Article.category == category)
    if trending:
        query = query.filter(models.Article.is_trending == True)
    
    articles = query.order_by(models.Article.created_at.desc()).all()
    
    if not articles:
        # Fallback for empty DB
        return [
            {
                "id": 1, "title": "The Secret Life of Fungi", "author": "Dr. Mycelium", "category": "Science",
                "content": "Discover how mushrooms communicate through the Wood Wide Web...", 
                "image_url": "https://images.unsplash.com/photo-1505820013142-f86a3439c5b2?w=800&q=80",
                "is_trending": True, "created_at": "2024-01-01T00:00:00"
            },
            {
                "id": 2, "title": "Foraging Safety 101", "author": "Nature Guide", "category": "Safety",
                "content": "A complete guide on how to spot toxic look-alikes in the wild...", 
                "image_url": "https://images.unsplash.com/photo-1544070078-a212eda27b49?w=800&q=80",
                "is_trending": False, "created_at": "2024-01-01T00:00:00"
            }
        ]
    return articles

@router.get("/daily-note")
def get_daily_note():
    notes = [
        "Lion's Mane is known for its potential to improve cognitive function and nerve growth.",
        "When foraging, always follow the 'when in doubt, throw it out' rule to avoid toxic look-alikes.",
        "Mushrooms are a great source of Vitamin D when exposed to sunlight during growth.",
        "Dried mushrooms have a much more intense flavor than fresh ones—perfect for soups!",
        "Amanita phalloides, known as the Death Cap, is responsible for the majority of mushroom fatalities."
    ]
    return {"note": random.choice(notes)}

@router.get("/recipes")
def get_recipes():
    """
    Returns featured mushroom recipes.
    """
    return [
        {
            "id": 1, "title": "Creamy Wild Mushroom Risotto", "time": "45 min", "difficulty": "Medium",
            "image": "https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=800&q=80"
        },
        {
            "id": 2, "title": "Garlic Butter Oyster Mushrooms", "time": "15 min", "difficulty": "Easy",
            "image": "https://images.unsplash.com/photo-1563814039166-07409f583f7c?w=800&q=80"
        },
        {
            "id": 3, "title": "Stuffed Portobello Caps", "time": "30 min", "difficulty": "Easy",
            "image": "https://images.unsplash.com/photo-1445506019300-204a9f993f3c?w=800&q=80"
        }
    ]
