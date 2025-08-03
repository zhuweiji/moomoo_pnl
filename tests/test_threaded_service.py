import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.utilities.threaded_service import ThreadedService


# Mock implementation for testing
class MockThreadedService(ThreadedService):
    def __init__(self, check_interval_seconds: int = 1):
        super().__init__(check_interval_seconds)
        self.running = False
        self.monitor_thread = None
        self.run_count = 0
        self.run_called = []

    def run(self, *args, **kwargs):
        """Mock implementation that tracks calls"""
        self.run_count += 1
        self.run_called.append((args, kwargs))


@pytest.fixture
def service():
    """Fixture to provide a clean MockThreadedService instance for each test."""
    service = MockThreadedService(check_interval_seconds=0.1)  # type: ignore
    yield service
    # Cleanup after each test
    if service.running:
        service.stop()


class TestThreadedService:
    def test_initialization(self):
        """Test that service initializes correctly."""
        service = MockThreadedService(check_interval_seconds=5)
        assert service.check_interval_seconds == 5
        assert service.running is False
        assert service.monitor_thread is None

    def test_default_check_interval(self):
        """Test default check interval is set correctly."""
        service = MockThreadedService()
        assert service.check_interval_seconds == 1

    def test_start_service(self, service):
        """Test that service starts correctly."""
        assert service.running is False
        assert service.monitor_thread is None

        service.start()

        assert service.running is True
        assert service.monitor_thread is not None
        assert service.monitor_thread.is_alive()
        assert service.monitor_thread.daemon is True

    def test_start_already_running_service(self, service):
        """Test that starting an already running service does nothing."""
        service.start()
        original_thread = service.monitor_thread

        # Try to start again
        service.start()

        # Should be the same thread
        assert service.monitor_thread is original_thread
        assert service.running is True

    def test_stop_service(self, service):
        """Test that service stops correctly."""
        service.start()
        assert service.running is True

        service.stop()

        assert service.running is False
        assert service.monitor_thread is None

    def test_stop_not_running_service(self, service):
        """Test that stopping a non-running service works without error."""
        assert service.running is False
        assert service.monitor_thread is None

        # Should not raise an exception
        service.stop()

        assert service.running is False
        assert service.monitor_thread is None

    def test_run_method_called_periodically(self, service):
        """Test that run method is called periodically."""
        service.start()

        # Wait for a few cycles
        time.sleep(0.35)  # Should allow for 3+ calls with 0.1s interval

        service.stop()

        # run() should have been called multiple times
        assert service.run_count > 2

    @patch("time.sleep")
    def test_monitor_loop_sleep_interval(self, mock_sleep):
        """Test that monitor loop uses correct sleep interval."""
        # Create service with specific interval
        service = MockThreadedService(check_interval_seconds=2)
        service.running = True

        # Mock sleep to avoid actual waiting, but stop after first call
        def stop_after_sleep(*args):
            service.running = False

        mock_sleep.side_effect = stop_after_sleep

        # Run one iteration of the monitor loop
        service._monitor_loop()

        # Verify sleep was called with correct interval
        mock_sleep.assert_called_once_with(2)

    @patch("threading.Thread")
    def test_thread_creation(self, mock_thread, service):
        """Test that thread is created with correct parameters."""
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        service.start()

        # Verify thread was created correctly
        mock_thread.assert_called_once_with(target=service._monitor_loop)
        mock_thread_instance.start.assert_called_once()
        assert mock_thread_instance.daemon is True

    def test_exception_handling_in_monitor_loop(self):
        """Test that exceptions in run() don't crash the monitor loop."""

        class ExceptionService(ThreadedService):
            def __init__(self):
                super().__init__(check_interval_seconds=0.05)  # type: ignore
                self.running = False
                self.monitor_thread = None
                self.call_count = 0

            def run(self):
                self.call_count += 1
                if self.call_count <= 2:
                    raise Exception("Test exception")

                # Stop after a few calls to end the test
                if self.call_count >= 4:
                    self.running = False

        service = ExceptionService()

        with patch("logging.getLogger") as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            service.start()

            # Wait for the service to run and stop itself
            time.sleep(0.3)

            # Verify that run was called multiple times despite exceptions
            assert service.call_count >= 4


class TestThreadedServiceAbstract:
    """Test that ThreadedService is properly abstract."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ThreadedService cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ThreadedService()  # type: ignore

    def test_must_implement_run_method(self):
        """Test that subclasses must implement run method."""

        class IncompleteService(ThreadedService):
            def __init__(self):
                super().__init__()
                self.running = False
                self.monitor_thread = None

            # Missing run() implementation

        with pytest.raises(TypeError):
            IncompleteService()  # type: ignore
