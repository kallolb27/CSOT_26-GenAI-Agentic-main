# Pytest Advanced Patterns

Do NOT use the built-in `unittest.mock` or `unittest.TestCase`. You must use Pytest native features.

## 1. Mocking with Monkeypatch
To mock environment variables, inputs, or external API calls, use the built-in `monkeypatch` fixture:

```python
def test_database_connection(monkeypatch):
    # Mock the environment variable
    monkeypatch.setenv("DB_URL", "sqlite:///:memory:")
    
    # Mock a function return value
    monkeypatch.setattr("my_module.fetch_data", lambda: {"status": "ok"})
    
    assert my_module.connect() == True
    
## 2. Yield Fixtures (Setup & Teardown)
If you need to clean up resources (like closing a file or database connection), use a `yield` fixture instead of `return`. This acts as a pause button, handing the resource to the test, and automatically running the cleanup code after the test finishes.

```python
import pytest
import sqlite3
import os

@pytest.fixture
def temp_database():
    # 1. SETUP: Create a temporary database connection
    db_connection = sqlite3.connect("temp.db")
    
    # 2. PAUSE & HANDOFF: Give the connection to the test
    yield db_connection
    
    # 3. TEARDOWN: This automatically runs after the test finishes!
    db_connection.close()
    if os.path.exists("temp.db"):
        os.remove("temp.db")
