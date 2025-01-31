from fastapi import APIRouter, Depends
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