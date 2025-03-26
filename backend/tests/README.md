# Backend Tests

This directory contains all backend tests for the Open WebUI project.

## Directory Structure

- `unit/`: Unit tests for individual components and functions
- `integration/`: Integration tests for component interactions
- `e2e/`: End-to-end tests for complete workflows
- `data/`: Test data and fixtures

## Test Guidelines

### 1. Test File Naming Convention
- All test files must start with `test_`
- File names should clearly describe the test content, e.g., `test_token.py`, `test_attachment.py`

### 2. Test Function Naming Convention
- Test functions must start with `test_`
- Function names should clearly describe the test scenario, e.g., `test_token_validation`, `test_attachment_sending`

### 3. Test Code Structure
- Each test file should include necessary imports
- Test functions should have clear docstrings explaining their purpose
- Use `pytest.mark.asyncio` decorator for async test functions
- Use fixtures to provide test data

### 4. Test Coverage Requirements
- Unit tests should cover core functionality
- Include both normal and error scenarios
- Use `pytest-cov` to generate coverage reports

### 5. Test Data Management
- Use fixtures to manage test data
- Sensitive data (e.g., tokens) should be injected via environment variables
- Use temporary files for file operation tests

## Test Categories

### Unit Tests
- Individual function tests
- Component-level tests
- Mock external dependencies

### Integration Tests
- API endpoint tests
- Database interaction tests
- Service integration tests

### E2E Tests
- Complete workflow tests
- User journey tests
- System-wide tests

## Running Tests

### 1. Install Test Dependencies
```bash
pip install -r requirements-test.txt
```

### 2. Set Environment Variables (Optional)
```bash
export TEST_TOKEN="your_test_token"
export TEST_RECIPIENT_EMAIL="test@example.com"
```

### 3. Run Test Commands

#### Run All Tests
```bash
pytest
```

#### Run Specific Test Types
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v
```

#### Run Specific Test Files
```bash
pytest tests/unit/mail/test_token.py -v
pytest tests/unit/mail/test_attachment.py -v
```

#### Run Tests with Coverage Report
```bash
pytest tests/ --cov=backend --cov-report=html -v
```

### 4. Test Output Description
- `-v`: Show verbose output
- `--cov`: Generate coverage report
- `--cov-report=html`: Generate HTML format coverage report

## Test Examples

### 1. Email Token Validation Test
```python
@pytest.mark.asyncio
async def test_token_validation(token):
    """Test token validation functionality"""
    # Test code...
```

### 2. Attachment Sending Test
```python
@pytest.mark.asyncio
async def test_attachment_sending(token, recipient_email, attachment_path):
    """Test attachment sending functionality"""
    # Test code...
```

## Test Fixtures

### 1. Common Fixtures
- `token`: Provides test access token
- `recipient_email`: Provides test recipient email
- `attachment_path`: Provides test attachment file path

### 2. Using Fixtures
```python
def test_something(token, recipient_email):
    # Using fixtures
    assert token is not None
    assert recipient_email is not None
```

## Best Practices

### 1. Test Isolation
- Each test function should be independent
- Use fixtures to provide test data, avoid test dependencies

### 2. Error Handling
- Tests should include error scenario handling
- Use try-except to catch and log errors

### 3. Logging
- Use `safe_log` function to log important information during tests
- Log test start, end, and key steps

### 4. Configuration Management
- Use `ConfigParser` to manage test configuration
- Avoid hardcoding sensitive information

## Common Issues

### 1. Async Testing
- Ensure `pytest.mark.asyncio` decorator is used
- Use `async/await` syntax
- Handle async function return values correctly

### 2. Environment Variables
- Check if environment variables are set correctly
- Use default values for unset environment variables

### 3. File Operations
- Use `tmp_path` fixture to create temporary files
- Clean up temporary files after tests

## Maintenance Instructions

### 1. Adding New Tests
- Follow naming conventions
- Add necessary docstrings
- Use fixtures to manage test data

### 2. Modifying Existing Tests
- Maintain backward compatibility
- Update related documentation
- Ensure test coverage

### 3. Test Dependency Updates
- Regularly update `requirements-test.txt`
- Test new version compatibility
- Update related documentation 
