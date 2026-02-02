"""
File upload/download API endpoints
"""
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiofiles

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.file import File

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a file
    
    - **file**: File to upload (image or document)
    
    Returns file ID and metadata
    """
    # Validate file size
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    # Validate file type
    allowed_types = settings.ALLOWED_IMAGE_TYPES + settings.ALLOWED_DOC_TYPES
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {file.content_type} not allowed"
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create upload directory if doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(contents)
    
    # Save to database
    db_file = File(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        mime_type=file.content_type,
        size=file_size,
        storage_path=file_path,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    
    return {
        "file_id": str(db_file.id),
        "filename": db_file.original_filename,
        "mime_type": db_file.mime_type,
        "size": db_file.size,
        "uploaded_at": db_file.uploaded_at,
    }


@router.get("/{file_id}")
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get file by ID
    
    - **file_id**: File ID
    """
    result = await db.execute(
        select(File).where(File.id == file_id)
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check ownership
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if file exists
    if not os.path.exists(file.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage"
        )
    
    return FileResponse(
        path=file.storage_path,
        filename=file.original_filename,
        media_type=file.mime_type,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete file
    
    - **file_id**: File ID
    """
    result = await db.execute(
        select(File).where(File.id == file_id)
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check ownership
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete from storage
    if os.path.exists(file.storage_path):
        os.remove(file.storage_path)
    
    # Delete from database
    await db.delete(file)
    await db.commit()
    
    return None
