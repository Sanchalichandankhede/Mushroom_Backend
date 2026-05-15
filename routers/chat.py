import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from database import get_db
import models, schemas
from auth_utils import get_current_user
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Initialize Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a Mushroom Expert AI assistant for the 'Mycelial Layer' app. "
    "You specialize in identifying mushrooms (based on descriptions), providing mushroom-based recipes, "
    "warning about toxic fungi, and offering general mycological advice. "
    "Always prioritize safety and explicitly warn users NEVER to consume mushrooms they cannot positively identify. "
    "Keep your tone professional, helpful, and premium. "
    "If a user asks about something unrelated to mushrooms, fungi, or nature, politely redirect them back to the application's focus."
)

@router.post("/", response_model=schemas.ChatResponse)
async def chat_with_expert(
    chat_req: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user)
):
    try:
        # Convert history from schema to google-genai format
        history = []
        if chat_req.history:
            for msg in chat_req.history:
                if msg.role == "user":
                    history.append(types.Content(role="user", parts=[types.Part(text=msg.text)]))
                else:
                    history.append(types.Content(role="model", parts=[types.Part(text=msg.text)]))

        # Create chat session with system instruction
        chat = client.chats.create(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            ),
            history=history
        )

        # Send the message
        response = chat.send_message(chat_req.message)
        
        return schemas.ChatResponse(response=response.text)

    except Exception as e:
        print(f"Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Service Error: {str(e)}")
