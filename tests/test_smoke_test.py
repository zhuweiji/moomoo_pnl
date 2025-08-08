#!/usr/bin/env python3
"""
Smoke test for the service - runs the service for 5 seconds and checks for failures.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from src.core.utilities import get_logger

log = get_logger(__name__)


def test_run_smoke_test():
    """Run the service for 5 seconds and check if it starts successfully."""

    # Path to your main.py file
    main_py_path = "src.main"

    process = None
    try:
        # Start the service as a subprocess
        process = subprocess.Popen([sys.executable, "-m", main_py_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Wait for 5 seconds
        time.sleep(5)

        # Check if process is still running
        poll_result = process.poll()

        if poll_result is None:
            return
        else:
            log.exception(f"Service exited with code {poll_result}")

            # Print stdout and stderr for debugging
            stdout, stderr = process.communicate()
            if stdout:
                log.error(f"STDOUT:\n{stdout}")
            if stderr:
                log.error(f"STDERR:\n{stderr}")

            raise Exception

    except FileNotFoundError:
        raise
    except Exception as e:
        raise

    finally:
        # Clean up: terminate the process if it's still running
        if process and process.poll() is None:
            try:
                # Try graceful termination first
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # If graceful termination fails, force kill
                process.kill()
                process.wait()
