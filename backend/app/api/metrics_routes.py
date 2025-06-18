from datetime import datetime, timezone
from typing import Any, Dict
import uuid
import socket

import psutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.metrics import MetricCreate, MetricResponse, MetricUpdate
from app.services.metrics_repository import MetricsRepository
from app.services.metrics.simplified_metrics_service import SimplifiedMetricsService

router = APIRouter(tags=["metrics"])

@router.get("/system", response_model=dict)
async def get_system_metrics():
    """
    Retrieve basic system metrics.
    """
    try:
        # Collect metrics
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        network_io = {
            'sent': psutil.net_io_counters().bytes_sent,
            'recv': psutil.net_io_counters().bytes_recv
        }
        process_count = len(psutil.pids())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create a dictionary to store additional details
        details = {
            'cpu': {
                'percent': cpu_usage,
                'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'core_count': psutil.cpu_count(logical=False),
                'thread_count': psutil.cpu_count(logical=True)
            },
            'memory': {
                'percent': memory_usage,
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'used': psutil.virtual_memory().used,
                'free': psutil.virtual_memory().free,
                'buffer': getattr(psutil.virtual_memory(), 'buffers', 0),
                'cache': getattr(psutil.virtual_memory(), 'cached', 0)
            },
            'disk': {
                'percent': disk_usage,
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'available': psutil.disk_usage('/').free
            },
            'network': {
                'bytes_sent': network_io['sent'],
                'bytes_recv': network_io['recv'],
                'packets_sent': psutil.net_io_counters().packets_sent,
                'packets_recv': psutil.net_io_counters().packets_recv
            }
        }

        # Return the collected metrics
        return {
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'network_io': network_io,
            'process_count': process_count,
            'timestamp': timestamp,
            'details': details
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system metrics: {str(error)}")

@router.post("/", response_model=MetricResponse)
async def create_metric(
    metric_create: MetricCreate, 
    current_user: dict = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Sir Hawkington's Metric Creation Endpoint
    """
    try:
        # Set the user ID from the current user
        metric_data = metric_create.model_dump()
        metric_data["user_id"] = current_user["id"]
        metrics_repo = MetricsRepository()
        return await metrics_repo.create_metric(db_session, metric_data)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[MetricResponse])
async def read_user_metrics(
    skip: int = 0, 
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db)
):
    """
    Retrieve paginated metrics for the current user.
    """
    metrics_repository = MetricsRepository()
    user_metrics = await metrics_repository.get_user_metrics(
        db_session, current_user['id'], skip, limit
    )
    return user_metrics

@router.get("/{metric_id}", response_model=MetricResponse)
async def read_metric_by_id(
    metric_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db)
) -> MetricResponse:
    """
    Retrieve a metric by ID.
    """
    metrics_repository = MetricsRepository()
    metric = await metrics_repository.get_metric_by_id(db_session, metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    if str(metric.user_id) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this metric")

    return metric

@router.put("/{metric_id}", response_model=MetricResponse)
async def update_metric_by_id(
    metric_id: uuid.UUID,
    metric_update_data: MetricUpdate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetricResponse:
    """
    Update a metric by ID.
    """
    metrics_repository = MetricsRepository()
    metric = await metrics_repository.get_metric_by_id(db_session, metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    if str(metric.user_id) != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this metric")

    return await metrics_repository.update_metric(db_session, metric_id, metric_update_data)

@router.delete("/{metric_id}")
async def delete_metric(
    metric_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
) -> Dict[str, bool]:
    """
    The Meth Snail's Metric Deletion Endpoint
    """

    metrics_repository = MetricsRepository()
    metric = await metrics_repository.get_metric_by_id(db_session, metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    if str(metric.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this metric")

    deleted = await metrics_repository.delete_metric(db_session, metric_id)

    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete metric")

    return {"deleted": True}
