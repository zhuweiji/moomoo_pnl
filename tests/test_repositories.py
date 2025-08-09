import pytest


import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, mock_open
from typing import Collection, Dict, Any


from src.core.utilities.repositories import Repository, JsonFileRepository, JsonSerializable


def test_abstract_repository_cannot_be_created():
    with pytest.raises(TypeError):
        Repository()  # type: ignore


def test_abstract_JsonSerializable_cannot_be_created():
    with pytest.raises(TypeError):
        JsonSerializable()  # type: ignore


# Mock classes for testing
class MockJsonSerializable(JsonSerializable):
    """Mock class implementing JsonSerializable interface."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return self.data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MockJsonSerializable":
        return cls(data)

    def __eq__(self, other):
        if not isinstance(other, MockJsonSerializable):
            return False
        return self.data == other.data


class TestJsonFileRepository:
    """Test suite for JsonFileRepository class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "test_data.json"
        self.item_class = MockJsonSerializable
        self.repository = JsonFileRepository(self.storage_path, self.item_class)

    def teardown_method(self):
        """Clean up after each test method."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test repository initialization."""
        repo = JsonFileRepository(Path("test.json"), MockJsonSerializable)  # type: ignore
        assert repo.storage_path == Path("test.json")
        assert repo.item_class == MockJsonSerializable

    def test_save_empty_collection(self):
        """Test saving an empty collection."""
        empty_items = []

        self.repository.save_all(empty_items)

        assert self.storage_path.exists()
        with open(self.storage_path, "r") as f:
            data = json.load(f)
        assert data == []

    def test_save_single_item(self):
        """Test saving a single item."""
        item = MockJsonSerializable({"id": 1, "name": "test"})
        items = [item]

        self.repository.save_all(items)

        assert self.storage_path.exists()
        with open(self.storage_path, "r") as f:
            data = json.load(f)

        expected = [{"id": 1, "name": "test"}]
        assert data == expected

    def test_save_multiple_items(self):
        """Test saving multiple items."""
        items = [
            MockJsonSerializable({"id": 1, "name": "item1"}),
            MockJsonSerializable({"id": 2, "name": "item2"}),
            MockJsonSerializable({"id": 3, "name": "item3"}),
        ]

        self.repository.save_all(items)

        with open(self.storage_path, "r") as f:
            data = json.load(f)

        expected = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}, {"id": 3, "name": "item3"}]
        assert data == expected

    def test_save_creates_parent_directories(self):
        """Test that save creates parent directories if they don't exist."""
        nested_path = Path(self.temp_dir.name) / "nested" / "path" / "test.json"
        repository = JsonFileRepository(nested_path, self.item_class)

        items = [MockJsonSerializable({"test": "data"})]
        repository.save_all(items)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_save_handles_file_write_error(self, mock_file):
        """Test that save handles file write errors properly."""
        items = [MockJsonSerializable({"test": "data"})]

        with pytest.raises(IOError, match="Permission denied"):
            self.repository.save_all(items)

    @patch("json.dump", side_effect=json.JSONEncoder().encode)
    def test_save_with_json_serialization_error(self, mock_dump):
        """Test save handles JSON serialization errors.

        This test case realistically shouldn't ever happen probably"""
        mock_dump.side_effect = TypeError("Object not JSON serializable")
        items = [MockJsonSerializable({"test": "data"})]

        with pytest.raises(TypeError, match="Object not JSON serializable"):
            self.repository.save_all(items)

    def test_load_empty_file(self):
        """Test loading from an empty JSON file."""
        # Create empty JSON array file
        with open(self.storage_path, "w") as f:
            json.dump([], f)

        result = self.repository.get_all()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_load_single_item(self):
        """Test loading a single item."""
        test_data = [{"id": 1, "name": "test"}]
        with open(self.storage_path, "w") as f:
            json.dump(test_data, f)

        result = self.repository.get_all()

        assert len(result) == 1
        assert result[0].data == {"id": 1, "name": "test"}

    def test_load_multiple_items(self):
        """Test loading multiple items."""
        test_data = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}, {"id": 3, "name": "item3"}]
        with open(self.storage_path, "w") as f:
            json.dump(test_data, f)

        result = self.repository.get_all()

        assert len(result) == 3
        assert result[0].data == {"id": 1, "name": "item1"}
        assert result[1].data == {"id": 2, "name": "item2"}
        assert result[2].data == {"id": 3, "name": "item3"}

    def test_load_when_file_does_not_exist(self):
        nested_path = Path(self.temp_dir.name) / "nested" / "path" / "test.json"
        repository = JsonFileRepository(nested_path, self.item_class)

        # no error should be raised
        repository.get_all()

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_load_handles_file_read_error(self, mock_file):
        """Test that load handles file read errors properly."""
        with pytest.raises(IOError, match="Permission denied"):
            self.repository.get_all()

    def test_load_handles_invalid_json(self):
        """Test load handles invalid JSON content."""
        # Write invalid JSON to file
        with open(self.storage_path, "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            self.repository.get_all()

    def test_load_handles_item_class_error(self):
        """Test load handles errors in item_class.from_dict()."""
        # Create a mock item class that raises an error
        error_item_class = Mock()
        error_item_class.from_dict.side_effect = ValueError("Invalid data")

        repository = JsonFileRepository(self.storage_path, error_item_class)  # type: ignore

        # Create valid JSON file
        test_data = [{"id": 1, "name": "test"}]
        with open(self.storage_path, "w") as f:
            json.dump(test_data, f)

        with pytest.raises(ValueError, match="Invalid data"):
            repository.get_all()

    def test_save_and_load_roundtrip(self):
        """Test that saved items can be loaded back correctly."""
        original_items = [
            MockJsonSerializable({"id": 1, "name": "item1", "value": 100}),
            MockJsonSerializable({"id": 2, "name": "item2", "value": 200}),
        ]

        # Save items
        self.repository.save_all(original_items)

        # Load items back
        loaded_items = self.repository.get_all()

        # Verify they match
        assert len(loaded_items) == len(original_items)
        for original, loaded in zip(original_items, loaded_items):
            assert original == loaded


class TestJsonFileRepositoryNonfunctional:
    """Additional tests for JsonFileRepository."""

    def test_concurrent_access(self):
        """Test repository behavior with concurrent access patterns."""
        with TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "concurrent_test.json"
            repo1 = JsonFileRepository(storage_path, MockJsonSerializable)
            repo2 = JsonFileRepository(storage_path, MockJsonSerializable)

            # Save with first repository
            items1 = [MockJsonSerializable({"id": 1, "source": "repo1"})]
            repo1.save_all(items1)

            # Load with second repository
            loaded_items = repo2.get_all()
            assert len(loaded_items) == 1
            assert loaded_items[0].data["source"] == "repo1"

            # Save with second repository
            items2 = [MockJsonSerializable({"id": 2, "source": "repo2"})]
            repo2.save_all(items2)

            # Load with first repository
            loaded_items = repo1.get_all()
            assert len(loaded_items) == 1
            assert loaded_items[0].data["source"] == "repo2"

    def test_large_dataset(self):
        """Test repository with a large number of items."""
        with TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "large_test.json"
            repository = JsonFileRepository(storage_path, MockJsonSerializable)

            # Create a large number of items
            large_items = [MockJsonSerializable({"id": i, "data": f"item_{i}"}) for i in range(1000)]

            # Save and load
            repository.save_all(large_items)
            loaded_items = repository.get_all()

            assert len(loaded_items) == 1000
            assert loaded_items[500].data["data"] == "item_500"
