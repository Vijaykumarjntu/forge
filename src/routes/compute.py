import subprocess
import tempfile

import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
import httpx

router = APIRouter()
from pydantic import BaseModel

class RunCodeRequest(BaseModel):
    code: str
    language: str = "python"

@router.post("/v1/run")
async def run_code(request: RunCodeRequest):
    code = request.code 
    language = request.language
    # print("we are inside the run code")
    # print(code)
    # print(language)
    if not code:
        
        raise HTTPException(400, "No code provided")
    print(code)
    if language == "python":
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Timeout after 10 seconds
            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Code execution timed out (10s limit)"}
        finally:
            os.unlink(temp_file)
    
    elif language == "javascript":
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ["node", temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Code execution timed out (10s limit)"}
        finally:
            os.unlink(temp_file)
    
    return {"error": f"Unsupported language: {language}"}