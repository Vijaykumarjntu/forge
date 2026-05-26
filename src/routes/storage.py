import shutil
from fastapi import UploadFile, File

import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
import httpx
from fastapi.responses import FileResponse
router = APIRouter()

@router.post("/v1/upload")
# async def upload_file(api_key_hash: str, file: UploadFile = File(...)):
async def upload_file(file: UploadFile = File(...)):
    print("we are inside the upload file api")
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
    print("we are inside the get files")
    print(filename)
    return FileResponse(f"./uploads/{filename}")