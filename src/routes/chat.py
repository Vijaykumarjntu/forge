import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "mistral-small-latest"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

# Simple auth (replace with your actual auth)
def verify_api_key(api_key: str):
    expected = os.getenv("ADMIN_API_KEY", "test-key")
    if api_key != expected:
        raise HTTPException(401, "Invalid key")

@router.post("/v1/chat/completions")
async def chat_completion(
    request: ChatRequest,
    authorization: str = Depends(lambda: None)  # Placeholder
):
    # Manual auth check from header
    from fastapi import Request
    # This is simplified - add your actual auth
    
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise HTTPException(500, "MISTRAL_API_KEY not set")
    
    messages = [msg.dict() for msg in request.messages]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.text)
        
        data = response.json()
        
        return {
            "id": f"mistral-{datetime.now().timestamp()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": data["choices"][0]["message"]["content"]},
                "finish_reason": "stop"
            }],
            "usage": data.get("usage", {})
        }