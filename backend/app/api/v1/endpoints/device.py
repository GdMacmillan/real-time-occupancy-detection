from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timedelta
import aiofiles
import os
from ....db.session import get_session
from ....models.device import Device

router = APIRouter()

@router.get("/", response_model=List[Device])
async def get_devices(session: Session = Depends(get_session)):
    """Get all registered devices."""
    return session.exec(select(Device)).all()

@router.get("/{device_id}/image")
async def get_device_image(
    device_id: str,
    session: Session = Depends(get_session)
):
    """Get the latest scene image for a device."""
    device = session.exec(
        select(Device).where(Device.device_id == device_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    if not device.latest_image_path or not os.path.exists(device.latest_image_path):
        raise HTTPException(status_code=404, detail="No image available")
        
    # Check if image is older than 2 minutes
    image_time = datetime.fromtimestamp(os.path.getmtime(device.latest_image_path))
    if datetime.now() - image_time > timedelta(minutes=2):
        raise HTTPException(status_code=404, detail="Image too old")
    
    async with aiofiles.open(device.latest_image_path, mode='rb') as f:
        content = await f.read()
    return Response(content, media_type="image/jpeg")

@router.put("/{device_id}/alert")
async def toggle_device_alert(
    device_id: str,
    enable: bool,
    session: Session = Depends(get_session)
):
    """Toggle alert settings for a device."""
    device = session.exec(
        select(Device).where(Device.device_id == device_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.alert_enabled = enable
    session.add(device)
    session.commit()
    session.refresh(device)
    return device 