# Tests

This directory contains comprehensive tests for the caller application.

## Test Structure

- `test_openai_service.py` - Tests for the OpenAI service functionality
- `test_audio_service.py` - Tests for the audio service functionality
- `conftest.py` - Pytest configuration and common fixtures
- `requirements-test.txt` - Testing dependencies

## Running Tests

### Install Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

### Run All Tests

```bash
# From the project root
python run_tests.py

# Or directly with pytest
pytest tests/ -v
```

### Run Specific Test Files

```bash
# Run only OpenAI service tests
python run_tests.py test_openai_service.py

# Run only audio service tests
python run_tests.py test_audio_service.py
```

### Run Tests with Coverage

```bash
pytest tests/ -v --cov=. --cov-report=html
```

## Test Coverage

### OpenAI Service Tests

- **Initialization**: Service setup, environment variable handling
- **Message Building**: Conversation history management, system message generation
- **Call State Management**: Parsing, updating, and querying call state information
- **OpenAI Integration**: API communication, streaming responses, error handling
- **Transcript Processing**: Handling incoming transcripts from the server
- **WebSocket Communication**: Connection management, message handling

### Audio Service Tests

- **Initialization**: Service setup, DeepGram configuration
- **DeepGram Integration**: Connection management, URL building, API key handling
- **Audio Processing**: Sending audio data, handling different audio formats
- **Message Handling**: Processing DeepGram responses, transcript extraction
- **Control Messages**: Finalize and keepalive message handling
- **Queue Management**: Transcript queue operations
- **Error Handling**: Connection failures, invalid data handling

## Test Features

- **Async Testing**: All async functions are properly tested with `pytest-asyncio`
- **Mocking**: External dependencies (OpenAI, DeepGram, WebSockets) are mocked
- **Environment Isolation**: Tests use isolated environment variables
- **Comprehensive Coverage**: Tests cover success cases, error cases, and edge cases
- **Realistic Data**: Tests use realistic audio data and conversation examples

## Writing New Tests

When adding new functionality, follow these guidelines:

1. **Test Structure**: Use descriptive test method names and docstrings
2. **Fixtures**: Use pytest fixtures for common setup
3. **Mocking**: Mock external dependencies to avoid API calls during testing
4. **Async Testing**: Use `@pytest.mark.asyncio` for async test methods
5. **Error Cases**: Always test error conditions and edge cases
6. **Isolation**: Each test should be independent and not rely on other tests

## Example Test

```python
@pytest.mark.asyncio
async def test_example_functionality(service):
    """Test example functionality with proper mocking."""
    with patch.object(service, 'external_dependency', new_callable=AsyncMock) as mock_dep:
        mock_dep.return_value = "expected_result"
        
        result = await service.example_method("test_input")
        
        assert result == "expected_result"
        mock_dep.assert_called_once_with("test_input")
``` 