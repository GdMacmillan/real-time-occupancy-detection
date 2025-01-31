from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from ....db.session import get_session
from ....models.detection import Detection
from ....core.logging import get_logger

router = APIRouter()
logger = get_logger("backend.detection")

@router.get("/", response_model=List[Detection])
async def get_detections(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get historical detection events."""
    logger.debug(f"Fetching detections with skip={skip}, limit={limit}")
    query = select(Detection).offset(skip).limit(limit)
    results = session.exec(query).all()
    logger.info(f"Retrieved {len(results)} detection events")
    return results

@router.get("/stats")
async def get_detection_stats(session: Session = Depends(get_session)):
    """Get basic detection statistics."""
    logger.debug("Calculating detection statistics")
    total = session.exec(select(Detection)).count()
    detected = session.exec(
        select(Detection).where(Detection.detected == True)
    ).count()
    
    stats = {
        "total_events": total,
        "detection_count": detected,
        "detection_rate": detected / total if total > 0 else 0
    }
    logger.info(
        f"Detection stats: {detected}/{total} events detected "
        f"({stats['detection_rate']:.1%} detection rate)"
    )
    return stats

@router.get("/latest/{device_id}")
async def get_latest_detection(
    device_id: str,
    session: Session = Depends(get_session)
):
    """Get the most recent detection event for a device."""
    detection = session.exec(
        select(Detection)
        .where(Detection.device_id == device_id)
        .order_by(Detection.timestamp.desc())
        .limit(1)
    ).first()
    
    if not detection:
        raise HTTPException(status_code=404, detail="No detection events found")
        
    return detection

@router.get("/history/{device_id}")
async def get_detection_history(
    device_id: str,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get detection history for a device."""
    detections = session.exec(
        select(Detection)
        .where(Detection.device_id == device_id)
        .order_by(Detection.timestamp.desc())
        .limit(limit)
    ).all()
    
    return {
        "device_id": device_id,
        "events": detections,
        "total_events": len(detections)
    } 