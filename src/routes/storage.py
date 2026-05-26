import shutil
from fastapi import UploadFile, File

import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
import httpx

router = APIRouter()

@router.post("/v1/upload")
async def upload_file(api_key_hash: str, file: UploadFile = File(...)):
    os.makedirs("./uploads", exist_ok=True)
    file_path = f"./uploads/{datetime.now().timestamp()}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "file_path": file_path,
        "filename": file.filename,
        "size": os.path.getsize(file_path),
        "url": f"http://localhost:8000/v1/files/{os.path.basename(file_path)}"
    }

@router.get("/v1/files/{filename}")
async def get_file(filename: str):
    return FileResponse(f"./uploads/{filename}")