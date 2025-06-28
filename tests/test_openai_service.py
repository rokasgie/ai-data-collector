import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from openai_service import OpenAIService
from call_info import CallState, PatientInfo, CALL_STATE_EXPLANATIONS


class TestOpenAIService:
    @pytest.fixture
    def service(self):
        """Create a fresh OpenAIService instance for each test"""
        with patch('openai_service.openai.AsyncOpenAI'):
            service = OpenAIService()
            return service

    @pytest.fixture
    def mock_openai_client(self, service):
        """Mock OpenAI client"""
        service.openai_client = Mock()
        return service.openai_client

    def test_init(self, service):
        """Test service initialization"""
        assert service.conversation_history == []
        assert isinstance(service.call_state, CallState)
        assert isinstance(service.patient_info, PatientInfo)
        assert service.name == "Spike Bot"
        assert "Spike Clinical" in service.system_message

    def test_get_call_state_explanation_message(self, service):
        """Test call state explanation message generation"""
        # Set some call state values
        service.call_state.visit_limit = 20
        service.call_state.copay = 25.0
        service.call_state.deductible = 1000.0
        
        message = service.get_call_state_explanation_message()
        
        assert "visit_limit 20" in message
        assert "copay 25.0" in message
        assert "deductible 1000.0" in message
        assert "summarize the conversation in a single paragraph" in message

    def test_get_missing_information_message(self, service):
        """Test missing information message generation"""
        # Set some values, leave others None
        service.call_state.visit_limit = 20
        service.call_state.copay = None
        
        message = service.get_missing_information_message()
        
        assert "visit_limit_structure" in message
        assert "visit_limit -" not in message  # Should not be in missing info

    def test_get_system_message_first_conversation(self, service):
        """Test system message for first conversation"""
        service.conversation_history = [{"role": "user", "content": "test"}]
        
        message = service.get_system_message()
        
        assert message["role"] == "system"
        assert "Spike Clinical" in message["content"]

    def test_get_system_message_complete_info(self, service):
        """Test system message when all call state info is complete"""
        # Set all call state values
        for field in CALL_STATE_EXPLANATIONS.keys():
            setattr(service.call_state, field, "test_value")
        
        service.conversation_history = [
            {"role": "user", "content": "test1"},
            {"role": "assistant", "content": "test2"}
        ]
        
        message = service.get_system_message()
        
        assert message["role"] == "system"
        assert "summarize the conversation" in message["content"]

    def test_get_system_message_missing_info(self, service):
        """Test system message when some call state info is missing"""
        # Leave some values as None
        service.call_state.visit_limit = None
        service.call_state.copay = 25.0
        
        service.conversation_history = [
            {"role": "user", "content": "test1"},
            {"role": "assistant", "content": "test2"}
        ]
        
        message = service.get_system_message()
        
        assert message["role"] == "system"
        assert "ask the representative" in message["content"]

    def test_build_messages(self, service):
        """Test message building"""
        service.conversation_history = [
            {"role": "user", "content": "test1"},
            {"role": "assistant", "content": "test2"}
        ]
        
        messages = service.build_messages()
        
        assert len(messages) == 3  # system + 2 conversation messages
        assert messages[0]["role"] == "system"

    def test_build_messages_truncates_history(self, service):
        """Test that message history is truncated to 30 messages"""
        # Create 35 messages
        for i in range(35):
            service.conversation_history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"message {i}"
            })
        
        messages = service.build_messages()
        
        # Should have 31 messages (system + 30 from history)
        assert len(messages) == 31

    @pytest.mark.asyncio
    async def test_parse_response_success(self, service, mock_openai_client):
        """Test successful response parsing"""
        # Mock the parsing response
        mock_parsed_state = CallState(
            visit_limit=20,
            copay=25.0,
            deductible=1000.0
        )
        mock_response = Mock()
        mock_response.output_parsed = mock_parsed_state
        mock_openai_client.responses.parse = AsyncMock(return_value=mock_response)
        
        # Test parsing
        await service.parse_response([
            {"role": "user", "content": "What's the visit limit?"},
            {"role": "assistant", "content": "The visit limit is 20 visits per year."}
        ])
        
        # Verify call state was updated
        assert service.call_state.visit_limit == 20
        assert service.call_state.copay == 25.0
        assert service.call_state.deductible == 1000.0

    @pytest.mark.asyncio
    async def test_parse_response_none_result(self, service, mock_openai_client):
        """Test parsing when OpenAI returns None"""
        mock_response = Mock()
        mock_response.output_parsed = None
        mock_openai_client.responses.parse = AsyncMock(return_value=mock_response)
        
        # Should not raise an exception
        await service.parse_response([
            {"role": "user", "content": "test"}
        ])

    @pytest.mark.asyncio
    async def test_parse_response_exception(self, service, mock_openai_client):
        """Test parsing when OpenAI raises an exception"""
        mock_openai_client.responses.parse = AsyncMock(side_effect=Exception("API Error"))
        
        # Should not raise an exception, should log error
        await service.parse_response([
            {"role": "user", "content": "test"}
        ])

    @pytest.mark.asyncio
    async def test_send_to_openai_success(self, service, mock_openai_client):
        """Test successful OpenAI communication"""
        # Mock streaming response
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta.content = "Hello"
        
        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta.content = " there."
        
        # Create an async generator for the stream
        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
        
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        # Mock parsing
        with patch.object(service, 'parse_response', new_callable=AsyncMock):
            # Create a mock callback
            mock_callback = AsyncMock()
            
            response = await service.send_to_openai("test transcript", mock_callback)
        
        # send_to_openai returns None, responses are sent via callback
        assert response is None
        assert len(service.conversation_history) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_send_to_openai_with_callback(self, service, mock_openai_client):
        """Test OpenAI communication with response callback"""
        # Mock streaming response
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta.content = "Hello there."
        
        # Create an async generator for the stream
        async def mock_stream():
            yield mock_chunk
        
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        # Mock parsing
        with patch.object(service, 'parse_response', new_callable=AsyncMock):
            # Create a mock callback
            async def mock_callback(content):
                assert content == "Hello there."
            
            response = await service.send_to_openai("test transcript", mock_callback)
        
        # send_to_openai returns None, responses are sent via callback
        assert response is None

    @pytest.mark.asyncio
    async def test_send_to_openai_exception(self, service, mock_openai_client):
        """Test OpenAI communication when an exception occurs"""
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        # Create a mock callback
        mock_callback = AsyncMock()
        
        # Should not raise an exception, should return None
        response = await service.send_to_openai("test transcript", mock_callback)
        
        assert response is None


if __name__ == "__main__":
    pytest.main([__file__]) 