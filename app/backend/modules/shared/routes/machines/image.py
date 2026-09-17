import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs
from services.machines import MachinesService
from services.machine_image_storage import (
    ALLOWED_CONTENT_TYPES,
    delete_by_url,
    public_url,
    upload_machine_image,
)

router = APIRouter(prefix="/api/v1/entities/machines", tags=["machines"])
logger = logging.getLogger(__name__)


@router.post("/image", responses={
    400: {"description": "Invalid image"},
    500: {"description": "Internal Server Error"},
})
async def upload_pending_machine_photo(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """Upload a photo before the machine exists yet (creation flow).

    Stores the file in MinIO under a 'pending' key and returns its public URL —
    the caller attaches that URL to the machine on create. No DB row involved.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. "
                   f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    file_bytes = await file.read()
    try:
        object_key = upload_machine_image(
            "pending", file.filename or "photo.jpg", file_bytes, file.content_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to upload pending machine image: {e}")
        raise HTTPException(status_code=500, detail="Failed to store image")

    return {"image_url": public_url(object_key)}


@router.post("/{id}/image", responses={
    400: {"description": "Invalid image"},
    404: {"description": "Machines not found"},
    500: {"description": "Internal Server Error"},
})
async def upload_machine_photo(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """Upload a photo for a machine, store it in MinIO, and set machine.image_url."""
    service = MachinesService(db)
    machine = await service.get_by_id(id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machines not found")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. "
                   f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    file_bytes = await file.read()
    try:
        object_key = upload_machine_image(
            id, file.filename or "photo.jpg", file_bytes, file.content_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to upload machine image for {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store image")

    old_url = getattr(machine, "image_url", None)
    new_url = public_url(object_key)
    await service.update(id, {"image_url": new_url})

    delete_by_url(old_url)  # best-effort cleanup of the previous photo

    logger.info(f"Machine {id} image updated: {new_url}")
    return {"image_url": new_url}
