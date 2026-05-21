# 🍄 Mushroom Project — Python Backend

A FastAPI backend for a mushroom identification and marketplace app.

## Features

- **Authentication** — JWT-based register/login
- **Mushroom Encyclopedia** — Browse, search, filter mushrooms by category
- **AI Identification** — Upload a photo → get mushroom prediction + safety info
- **Marketplace** — Sellers list mushrooms for sale; buyers browse & buy
- **Cart & Orders** — Add to cart, place orders, track status, cancel orders

---

## Project Structure

```
mushroom_backend/
├── main.py               # FastAPI app entry point
├── database.py           # SQLAlchemy engine & session
├── models.py             # Database models (ORM)
├── schemas.py            # Pydantic request/response schemas
├── auth_utils.py         # JWT creation, password hashing, auth dependencies
├── requirements.txt
└── routers/
    ├── auth.py           # POST /api/auth/register, login, /me
    ├── mushrooms.py      # GET/POST/PUT/DELETE /api/mushrooms + listings
    ├── identification.py # POST /api/identify/upload
    ├── cart.py           # GET/POST/PUT/DELETE /api/cart
    └── orders.py         # POST /api/orders/place, GET, cancel
```

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Run the server
python main.py
# OR
uvicorn main:app --reload

# Alternative startup
# Windows PowerShell:
./run.ps1
# Windows CMD:
run.bat
```

API docs available at: **http://localhost:8000/docs**

---

## Environment Variables

| Variable       | Default                                          | Description                                               |
| -------------- | ------------------------------------------------ | --------------------------------------------------------- |
| `DATABASE_URL` | `sqlite:///./mushroom_project.db`                | Database connection string. Leave blank for local SQLite. |
| `SECRET_KEY`   | `mushroom-super-secret-key-change-in-production` | JWT signing secret                                        |

> If you need PostgreSQL, install `psycopg2-binary` separately and set `DATABASE_URL`.

---

## API Endpoints

### Auth

| Method | Endpoint             | Description              |
| ------ | -------------------- | ------------------------ |
| POST   | `/api/auth/register` | Register new user        |
| POST   | `/api/auth/login`    | Login and get JWT        |
| GET    | `/api/auth/me`       | Get current user profile |

### Mushrooms

| Method | Endpoint                      | Description                                    |
| ------ | ----------------------------- | ---------------------------------------------- |
| GET    | `/api/mushrooms/`             | List all mushrooms (filter by category/search) |
| GET    | `/api/mushrooms/{id}`         | Get mushroom detail                            |
| POST   | `/api/mushrooms/`             | Add mushroom (authenticated)                   |
| GET    | `/api/mushrooms/listings/all` | Browse marketplace listings                    |
| POST   | `/api/mushrooms/listings/`    | Create a listing (seller)                      |

### Identification

| Method | Endpoint                | Description                    |
| ------ | ----------------------- | ------------------------------ |
| POST   | `/api/identify/upload`  | Upload image → get prediction  |
| GET    | `/api/identify/history` | View your past identifications |

### Cart

| Method | Endpoint         | Description          |
| ------ | ---------------- | -------------------- |
| GET    | `/api/cart/`     | View cart with total |
| POST   | `/api/cart/add`  | Add item to cart     |
| PUT    | `/api/cart/{id}` | Update quantity      |
| DELETE | `/api/cart/{id}` | Remove item          |

### Orders

| Method | Endpoint                  | Description           |
| ------ | ------------------------- | --------------------- |
| POST   | `/api/orders/place`       | Place order from cart |
| GET    | `/api/orders/`            | View my orders        |
| GET    | `/api/orders/{id}`        | Order detail          |
| PUT    | `/api/orders/{id}/cancel` | Cancel pending order  |

---

## Integrating a Real ML Model

In `routers/identification.py`, replace `mock_ml_predict()`:

```python
# Example with HuggingFace transformers
from transformers import pipeline

classifier = pipeline("image-classification", model="your-mushroom-model")

def mock_ml_predict(image_path: str) -> dict:
    results = classifier(image_path)
    top = results[0]
    return {
        "predicted_name": top["label"],
        "confidence_score": top["score"],
        "category": "edible",  # map from your model labels
        "is_safe": True,
        "description": "...",
        "warnings": None,
    }
```

---

## Production Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Switch `DATABASE_URL` to PostgreSQL
- [ ] Set `allow_origins` in CORS to your frontend URL only
- [ ] Add rate limiting (e.g. `slowapi`)
- [ ] Store uploaded images on S3 or similar cloud storage
- [ ] Replace `mock_ml_predict` with a real trained model
