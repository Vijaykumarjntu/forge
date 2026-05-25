import os
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Mini AI Gateway", version="0.1")
security = HTTPBearer()

# ----- SQLite setup -----
DB_PATH = "gateway.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_hash TEXT,
                model TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                success BOOLEAN,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_api_key_hash ON requests(api_key_hash)")

init_db()

# ----- Rate limiting -----
rate_limit_store: Dict[str, List[datetime]] = {}
RATE_LIMIT_PER_MINUTE = 60

def check_rate_limit(api_key_hash: str) -> bool:
    now = datetime.now()
    if api_key_hash not in rate_limit_store:
        rate_limit_store[api_key_hash] = []
    
    cutoff = now - timedelta(minutes=1)
    rate_limit_store[api_key_hash] = [ts for ts in rate_limit_store[api_key_hash] if ts > cutoff]
    
    if len(rate_limit_store[api_key_hash]) >= RATE_LIMIT_PER_MINUTE:
        return False
    
    rate_limit_store[api_key_hash].append(now)
    return True

# ----- Request/Response models -----
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "mistral-small-latest"  # default
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

# ----- Auth -----
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    provided_key = credentials.credentials
    expected_key = os.getenv("MISTRAL_API_KEY", "test-key-123")
    # print("this is the provided key")
    # print(provided_key)
    # print("this is the expected key")
    # print(expected_key)
    if provided_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    key_hash = hashlib.sha256(provided_key.encode()).hexdigest()[:16]
    return key_hash

# ----- Mistral proxy -----
async def call_mistral(model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Dict:
    api_key = os.getenv("MISTRAL_API_KEY")
    print("we ware inside call mistral")
    print(api_key)
    if not api_key:
        raise HTTPException(status_code=500, detail="MISTRAL_API_KEY not set")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        print("this is the call mistral response")
        print(response)
        if response.status_code != 200:
            error_detail = response.text
            raise HTTPException(status_code=response.status_code, detail=f"Mistral API error: {error_detail}")
        
        data = response.json()
        usage = data.get("usage", {})
        return {
            "content": data["choices"][0]["message"]["content"],
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }

# ----- Log helper -----
def log_request(api_key_hash: str, model: str, prompt_tokens: int, 
                completion_tokens: int, total_tokens: int, 
                success: bool, error_message: str = None):
    with get_db() as db:
        db.execute("""
            INSERT INTO requests (api_key_hash, model, prompt_tokens, completion_tokens, total_tokens, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (api_key_hash, model, prompt_tokens, completion_tokens, total_tokens, success, error_message))

# ----- Main endpoint -----
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest, api_key_hash: str = Depends(verify_api_key)):
    # Rate limit
    print("start of chat complete")
    if not check_rate_limit(api_key_hash):
        raise HTTPException(status_code=429, detail="Rate limit exceeded (60 requests per minute)")
    
    # Convert messages to dicts
    messages = [msg.dict() for msg in request.messages]
    print("we are insie the chat completion")
    print(messages)
    try:
        result = await call_mistral(request.model, messages, request.temperature, request.max_tokens)
        
        # Log success
        log_request(api_key_hash, request.model, result["prompt_tokens"], 
                   result["completion_tokens"], result["total_tokens"], True)
        
        # Return OpenAI-compatible response
        return {
            "id": f"mistral-{datetime.now().timestamp()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result["content"]},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["total_tokens"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        log_request(api_key_hash, request.model, 0, 0, 0, False, str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ----- Usage endpoint -----
@app.get("/v1/usage")
async def get_usage(api_key_hash: str = Depends(verify_api_key)):
    print("yup working")
    with get_db() as db:
        row = db.execute("""
            SELECT 
                COUNT(*) as total_requests,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens
            FROM requests
            WHERE api_key_hash = ?
        """, (api_key_hash,)).fetchone()
        
        return {
            "total_requests": row["total_requests"] or 0,
            "successful_requests": row["successful_requests"] or 0,
            "total_prompt_tokens": row["total_prompt_tokens"] or 0,
            "total_completion_tokens": row["total_completion_tokens"] or 0,
            "total_tokens": row["total_tokens"] or 0
        }

@app.get("/v1/health")
async def health():
    print("health wokrking")
    return {"status": "ok", "provider": "mistral"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)