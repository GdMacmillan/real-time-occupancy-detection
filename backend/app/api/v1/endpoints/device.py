from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from typing import List, Dict
from datetime import datetime, timedelta
import aiofiles
import os
from ....db.session import get_session
from ....models.device import Device
from ....models.detection import Detection

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

@router.get("/status", response_model=List[Dict])
async def get_devices_status(session: Session = Depends(get_session)):
    """Get status of all devices with their latest detection info."""
    devices = session.exec(select(Device)).all()
    
    device_status = []
    for device in devices:
        # Get latest detection for this device
        latest_detection = session.exec(
            select(Detection)
            .where(Detection.device_id == device.device_id)
            .order_by(Detection.timestamp.desc())
            .limit(1)
        ).first()

        status = {
            "device_id": device.device_id,
            "name": device.name,
            "type": device.type,
            "is_online": device.is_online,
            "last_seen": device.last_seen,
            "alert_enabled": device.alert_enabled,
            "latest_detection": None if not latest_detection else {
                "timestamp": latest_detection.timestamp,
                "detected": latest_detection.detected,
                "count": latest_detection.count,
                "confidence": latest_detection.confidence
            }
        }
        device_status.append(status)
    
    return device_status

@router.get("/{device_id}/summary")
async def get_device_summary(
    device_id: str,
    timeframe: str = "1h",  # Options: 1h, 24h, 7d
    session: Session = Depends(get_session)
):
    """Get detection summary for a device over a specified timeframe."""
    device = session.exec(
        select(Device).where(Device.device_id == device_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Calculate time threshold based on timeframe
    now = datetime.utcnow()
    if timeframe == "1h":
        threshold = now - timedelta(hours=1)
    elif timeframe == "24h":
        threshold = now - timedelta(days=1)
    elif timeframe == "7d":
        threshold = now - timedelta(days=7)
    else:
        raise HTTPException(status_code=400, detail="Invalid timeframe")

    # Get detection statistics
    detections = session.exec(
        select(Detection)
        .where(Detection.device_id == device_id)
        .where(Detection.timestamp > threshold)
    ).all()

    total_detections = len(detections)
    occupied_count = sum(1 for d in detections if d.detected)

    return {
        "device_id": device_id,
        "timeframe": timeframe,
        "total_events": total_detections,
        "occupied_events": occupied_count,
        "occupancy_rate": occupied_count / total_detections if total_detections > 0 else 0,
        "last_seen": device.last_seen,
        "is_online": device.is_online
    } 