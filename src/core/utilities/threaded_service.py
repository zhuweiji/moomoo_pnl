import threading
import time
from abc import ABC, abstractmethod

from .config.constants import INTERNAL_THREADED_SERVICE_RUN_SECONDS
from .logger import get_logger

log = get_logger(__name__)


class ThreadedService(ABC):
    def __init__(self, check_interval_seconds: int = INTERNAL_THREADED_SERVICE_RUN_SECONDS) -> None:
        super().__init__()

        self.check_interval_seconds = check_interval_seconds

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    def _monitor_loop(self) -> None:
        """Main monitoring loop for checking orders."""
        while self.running:
            log.debug("polling..")

            try:
                self.run()
            except Exception as e:
                log.error(f"Error in monitor loop: {e}")
            time.sleep(self.check_interval_seconds)

    def start(self) -> None:
        """Start the order monitoring thread."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        log.info(f"{self.__class__} started")

    def stop(self) -> None:
        """Stop the order monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None

        log.info(f"{self.__class__} stopped")
