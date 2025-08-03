import logging
import os
from typing import Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.core.moomoo_client import MoomooClient
from src.core.utilities import get_logger

log = get_logger(__name__)
security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """Validate user credentials."""
    correct_username = os.getenv("SITE_MAIN_USER_USERNAME")
    correct_password = os.getenv("SITE_MAIN_USER_PASSWORD")

    if not (credentials.username == correct_username and credentials.password == correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
