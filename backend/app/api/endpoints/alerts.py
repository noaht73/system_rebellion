from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.alerts import SystemAlert, AlertSeverity
from app.schemas.alerts import (
    SystemAlert as SystemAlertSchema,
    SystemAlertCreate,
    SystemAlertUpdate,
    SystemAlertList
)

router = APIRouter()


@router.get("/", response_model=SystemAlertList)
async def get_system_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    severity: Optional[AlertSeverity] = None,
    is_read: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all system alerts for the current user.
    """
    query = select(SystemAlert).where(
        SystemAlert.user_id == current_user.id
    )
    
    if severity:
        query = query.where(SystemAlert.severity == severity)
    
    if is_read is not None:
        query = query.where(SystemAlert.is_read == is_read)
    
    query = query.order_by(SystemAlert.timestamp.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    # Count total alerts
    count_query = select(func.count()).select_from(SystemAlert).where(
        SystemAlert.user_id == current_user.id
    )
    
    if severity:
        count_query = count_query.where(SystemAlert.severity == severity)
    
    if is_read is not None:
        count_query = count_query.where(SystemAlert.is_read == is_read)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    return {"alerts": alerts, "total": total}


@router.post("/", response_model=SystemAlertSchema, status_code=status.HTTP_201_CREATED)
async def create_system_alert(
    alert_data: SystemAlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new system alert.
    """
    alert = SystemAlert(
        user_id=current_user.id,
        title=alert_data.title,
        message=alert_data.message,
        severity=alert_data.severity,
        additional_data=alert_data.additional_data,
        is_read=alert_data.is_read,
        timestamp=datetime.now(timezone.utc)
    )
    
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    
    return alert


@router.get("/{alert_id}", response_model=SystemAlertSchema)
async def get_system_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific system alert by ID.
    """
    query = select(SystemAlert).where(
        SystemAlert.id == alert_id,
        SystemAlert.user_id == current_user.id
    )
    
    result = await db.execute(query)
    alert = result.scalars().first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System alert not found"
        )
    
    return alert


@router.put("/{alert_id}", response_model=SystemAlertSchema)
async def update_system_alert(
    alert_id: UUID,
    alert_data: SystemAlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing system alert.
    """
    query = select(SystemAlert).where(
        SystemAlert.id == alert_id,
        SystemAlert.user_id == current_user.id
    )
    
    result = await db.execute(query)
    alert = result.scalars().first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System alert not found"
        )
    
    # Update alert fields
    if alert_data.title is not None:
        alert.title = alert_data.title
    if alert_data.message is not None:
        alert.message = alert_data.message
    if alert_data.severity is not None:
        alert.severity = alert_data.severity
    if alert_data.additional_data is not None:
        alert.additional_data = alert_data.additional_data
    if alert_data.is_read is not None:
        alert.is_read = alert_data.is_read
    
    await db.commit()
    await db.refresh(alert)
    
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a system alert.
    """
    query = select(SystemAlert).where(
        SystemAlert.id == alert_id,
        SystemAlert.user_id == current_user.id
    )
    
    result = await db.execute(query)
    alert = result.scalars().first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System alert not found"
        )
    
    await db.delete(alert)
    await db.commit()
    
    return None


@router.post("/{alert_id}/mark-as-read", response_model=SystemAlertSchema)
async def mark_alert_as_read(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific system alert as read.
    """
    query = select(SystemAlert).where(
        SystemAlert.id == alert_id,
        SystemAlert.user_id == current_user.id
    )
    
    result = await db.execute(query)
    alert = result.scalars().first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System alert not found"
        )
    
    alert.is_read = True
    
    await db.commit()
    await db.refresh(alert)
    
    return alert


@router.post("/mark-all-as-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_alerts_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark all system alerts as read for the current user.
    """
    query = select(SystemAlert).where(
        SystemAlert.user_id == current_user.id,
        SystemAlert.is_read == False
    )
    
    result = await db.execute(query)
    unread_alerts = result.scalars().all()
    
    for alert in unread_alerts:
        alert.is_read = True
    
    await db.commit()
    
    return None
