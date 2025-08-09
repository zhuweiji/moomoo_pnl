"""Repository classes for handling data persistence."""

import json
from abc import ABC, abstractmethod
from typing import Dict, Generic, List, Optional, Protocol, Type, TypeAlias, TypeVar, Mapping, Collection

from src.core.utilities import get_logger
from .types import Filepath

log = get_logger(__name__)


T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base class for repositories."""

    @abstractmethod
    def save_all(self, items: Collection[T]) -> None:
        """Save items to storage."""
        pass

    @abstractmethod
    def get_all(self) -> Collection[T]:
        """Load items from storage."""
        pass


class JsonSerializable(Protocol):
    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "JsonSerializable":
        pass


# Define the type variable with JsonSerializable constraint
J = TypeVar("J", bound=JsonSerializable)


class JsonFileRepository(Repository[J], Generic[J]):
    """Repository implementation that stores data in JSON files."""

    def __init__(self, storage_path: Filepath, item_class: Type[J]):
        self.storage_path = storage_path
        self.item_class = item_class

    def save_all(self, items: Collection[J]) -> None:
        """Save items to a JSON file, overwriting the old values"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            log.debug(f"Saving items to {self.storage_path}")

            items_data = [item.to_dict() for item in items]
            with open(self.storage_path, "w") as f:
                json.dump(items_data, f, indent=2)
                log.debug(f"Saved {len(items_data)} items to {self.storage_path}")
        except Exception as e:
            log.error(f"Failed to save items: {e}")
            raise

    def get_all(self) -> list[J]:
        """Load items from a JSON file."""

        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text("[]")

        if not self.storage_path.is_file():
            raise ValueError

        try:
            log.debug(f"Loading items from {self.storage_path}")

            with open(self.storage_path, "r") as f:
                json_data = json.load(f)
                log.debug(f"Read {len(json_data)} items from {self.storage_path}")

            return [self.item_class.from_dict(i) for i in json_data]  # type: ignore
        except Exception as e:
            log.error(f"Failed to load items: {e}")
            raise
