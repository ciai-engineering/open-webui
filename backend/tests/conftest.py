import pytest
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture to provide the path to test data directory."""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def test_env():
    """Fixture to set up test environment variables."""
    os.environ["TESTING"] = "true"
    # Add other test environment variables here
    yield
    # Clean up after tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"] 