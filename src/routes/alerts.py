import logging

from fastapi import APIRouter

from src.alerts import global_task_service
from src.core.utilities import get_logger

log = get_logger(__name__)

router = APIRouter()


@router.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
    """Endpoint to get task status"""
    return global_task_service.get_task_status(task_id)


@router.post("/tasks/{task_id}/start")
def start_task(task_id: str):
    """Endpoint to start a specific task"""
    global_task_service.start_task(task_id)
    return {"status": "Task started"}


@router.post("/tasks/{task_id}/stop")
def stop_task(task_id: str):
    """Endpoint to stop a specific task"""
    global_task_service.stop_task(task_id)
    return {"status": "Task stopped"}
