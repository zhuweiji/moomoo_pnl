import asyncio
import threading
from datetime import datetime
from typing import Any, Callable, Optional

from pydantic import BaseModel

from src.core.notifications.notification_service import send_notification
from src.core.utilities import get_logger

log = get_logger(__name__)


class TaskConfig(BaseModel):
    """Configuration for a registered task"""

    func: Callable[[], Any]  # The function to run
    interval_seconds: int  # How often to run the task
    condition: Optional[Callable[[Any], bool]] = (
        None  # Optional condition to trigger alert
    )
    alert_message: Optional[str] = None  # Custom alert message
    last_run: Optional[datetime] = None
    name: Optional[str] = None  # Readable short name for humans


class TaskService:
    """
    A generic service for running background tasks with conditional alerts

    Usage example:
    task_service = TaskService()
    task_service.register_task(
        func=get_usd_to_sgd_rate,
        interval_minutes=60,
        condition=lambda result: result['rate'] > 1.35,
        alert_message="USD to SGD rate is high!"
    )
    """

    def __init__(self):
        self.tasks: dict[str, TaskConfig] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    def register_task(
        self,
        func: Callable[[], Any],
        interval_seconds: int,
        condition: Optional[Callable[[Any], bool]] = None,
        alert_message: Optional[str] = None,
        name: Optional[str] = None,
    ) -> str:
        """
        Register a new task to be run periodically

        :param func: Function to run
        :param interval_seconds: How often to run the task
        :param condition: Optional condition to trigger alert
        :param alert_message: Optional custom alert message
        :return: Task ID
        """
        task_id = func.__name__
        self.tasks[task_id] = TaskConfig(
            func=func,
            interval_seconds=interval_seconds,
            condition=condition,
            alert_message=alert_message,
            name=name,
        )
        return task_id

    async def _run_task(self, task_id: str):
        """Internal method to run a specific task periodically"""
        task_config = self.tasks[task_id]

        while True:
            try:
                # Run the task
                result = task_config.func()
                log.info(f"ran task {task_config.name}")

                # Check if condition is met and send alert if needed
                if task_config.condition and task_config.condition(result):
                    alert_msg = (
                        task_config.alert_message
                        or f"Alert for task {task_config.name}"
                    )
                    log.info(f"sent alert for task function {task_config.name}")

                    send_notification(
                        message=f"{alert_msg}\nResult: {result}",
                        title=f"Task Alert: {task_config.name}",
                    )

                # Update last run time
                task_config.last_run = datetime.now()

                # Wait for the next interval
                await asyncio.sleep(task_config.interval_seconds)

            except Exception as e:
                log.error(f"Error in task {task_id}: {e}")
                await asyncio.sleep(task_config.interval_seconds)

    def _start_event_loop(self):
        """Run the event loop in a separate thread"""
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        try:
            self._event_loop.run_forever()
        except Exception as e:
            log.error(f"Event loop error: {e}")
        finally:
            self._event_loop.close()

    def start_task(self, task_id: str, use_thread: bool = True):
        """
        Start a specific registered task

        :param task_id: ID of the task to start
        :param use_thread: If True, starts tasks in a separate thread,
                           else tries to use the current event loop
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not registered")

        if task_id in self.running_tasks:
            return  # Task already running

        # If using a separate thread
        if use_thread:
            if not self._event_loop:
                self._loop_thread = threading.Thread(
                    target=self._start_event_loop, daemon=True
                )
                self._loop_thread.start()

                # Give the thread a moment to start
                while not self._event_loop:
                    import time

                    time.sleep(0.1)

            # Schedule the task in the separate event loop
            task = self._event_loop.call_soon_threadsafe(
                self._event_loop.create_task, self._run_task(task_id)
            )
            self.running_tasks[task_id] = task  # type: ignore

        # If not using a thread, try to use current event loop
        else:
            try:
                loop = asyncio.get_event_loop()
                task = loop.create_task(self._run_task(task_id))
                self.running_tasks[task_id] = task
            except RuntimeError:
                log.error(
                    "No running event loop. Use use_thread=True or run in an async context."
                )
                raise

    def stop_task(self, task_id: str):
        """Stop a specific task"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]

    def get_task_status(self, task_id: str) -> dict:
        """Get status of a specific task"""
        if task_id not in self.tasks:
            return {"error": "Task not found"}

        task_config = self.tasks[task_id]
        return {
            "last_run": task_config.last_run,
            "is_running": task_id in self.running_tasks,
        }
