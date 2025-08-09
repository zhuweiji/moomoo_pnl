"""OpenD process management utilities."""

import platform
import subprocess
from pathlib import Path

import psutil

from src.core.utilities import get_logger, top_level_dir

log = get_logger(__name__)


def ensure_opend_running():
    """Check if OpenD is running and start it if not."""
    # Check if OpenD is already running
    opend_process_name = "OpenD.exe" if platform.system() == "Windows" else "OpenD"
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] == opend_process_name:
            return True

    # If not running, start OpenD
    if platform.system() == "Windows":
        opend_path = top_level_dir / "moomoo_OpenD_9.2.5208_Windows" / "OpenD.exe"
        start_flags = {"creationflags": subprocess.CREATE_NEW_CONSOLE}
    else:
        opend_path = top_level_dir / "moomoo_OpenD_9.2.5208_Ubuntu16.04" / "OpenD"
        start_flags = {}

    if not opend_path.exists():
        log.error(f"OpenD executable not found at {opend_path}")
        raise FileNotFoundError(f"OpenD executable not found at {opend_path}")

    try:
        subprocess.Popen([str(opend_path)], cwd=opend_path.parent, **start_flags)  # type: ignore
        log.info(f"Started OpenD process at {opend_path}")
    except Exception as e:
        log.error(f"Failed to start OpenD: {e}")
        raise


class OpenD_PathNotSet(Exception):
    pass
