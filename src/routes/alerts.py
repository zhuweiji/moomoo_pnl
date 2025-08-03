import logging

from fastapi import APIRouter, HTTPException

from src.alerts import global_task_service
from src.core.utilities import get_logger

log = get_logger(__name__)

base_route = "/tasks"
router = APIRouter(prefix=base_route)


@router.get("")
def get_all_tasks():
    """Endpoint to get all tasks"""
    return {taskid: task.to_dict() for taskid, task in global_task_service.get_all_tasks().items()}


@router.get("/{task_id}")
def get_task_status(task_id: str):
    """Endpoint to get task status"""
    task = global_task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@router.post("/{task_id}/start")
def start_task(task_id: str):
    """Endpoint to start a specific task"""
    global_task_service.start_task(task_id)
    return {"status": "Task started"}


@router.post("/{task_id}/stop")
def stop_task(task_id: str):
    """Endpoint to stop a specific task"""
    global_task_service.stop_task(task_id)
    return {"status": "Task stopped"}
