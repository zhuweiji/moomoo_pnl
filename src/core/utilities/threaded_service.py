import asyncio
import threading
import time
from abc import ABC, abstractmethod

from .singleton import ABCSingletonMeta, Singleton

from .config.constants import INTERNAL_THREADED_SERVICE_RUN_SECONDS
from .logger import get_logger

log = get_logger(__name__)


class ThreadedService(ABC):
    """
    Abstract base class for building long-running threaded services with periodic checks.

    This class runs a background daemon thread that repeatedly executes the `run` method
    at a fixed interval (`check_interval_seconds`). Subclasses must implement the `run`
    method to define the actual task to perform on each iteration.

    Attributes:
        check_interval_seconds (int): Number of seconds to wait between each call to `run`.
        running (bool): Flag indicating whether the monitoring thread is running.
        monitor_thread (threading.Thread): The background monitoring thread.

    Methods:
        start(): Start the monitoring thread. Has no effect if already running.
        stop(): Stop the monitoring thread gracefully.
        run(): Abstract method to implement the task to execute periodically.

    Usage example:
        class MyService(ThreadedService):
            def run(self):
                print("Doing periodic work!")

        service = MyService(check_interval_seconds=10)
        service.start()

        # The service will now run `run()` every 10 seconds in a background thread.
        # Do other work here, or just wait...

        service.stop()  # Stop the background thread when done.
    """

    def __init__(self, check_interval_seconds: int = INTERNAL_THREADED_SERVICE_RUN_SECONDS) -> None:
        super().__init__()

        self.check_interval_seconds = check_interval_seconds
        self.running = False
        self.monitor_thread = None

    @abstractmethod
    def run(self, *args, **kwargs):
        """Async method to be implemented by subclasses."""
        pass

    def _monitor_loop(self) -> None:
        """Thread target: runs the event loop and periodically calls run()."""
        while self.running:
            log.debug("polling..")

            try:
                self.run()
            except Exception as e:
                log.error(f"Error in monitor loop: {e}")
            time.sleep(self.check_interval_seconds)

    def start(self) -> None:
        """Start the monitoring thread."""
        if self.running:
            return
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        log.info(f"{self.__class__.__name__} started")

    def stop(self) -> None:
        """Stop the monitoring thread."""
        if not self.running:
            return
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None
        log.info(f"{self.__class__.__name__} stopped")


class SingletonThreadedService(ThreadedService, metaclass=ABCSingletonMeta):
    pass
