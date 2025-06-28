import pytest
import asyncio
import json
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from audio_service import AudioService


class TestAudioService:
    @pytest.fixture
    def transcript_queue(self):
        """Create a transcript queue for testing"""
        return asyncio.Queue()

    @pytest.fixture
    def service(self, transcript_queue):
        """Create a fresh AudioService instance for each test"""
        return AudioService(transcript_queue, transcript_wait_time=0.5)

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection"""
        websocket = AsyncMock()
        websocket.send = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    def test_init(self, service, transcript_queue):
        """Test service initialization"""
        assert service.deepgram_ws is None
        assert service.transcript_queue == transcript_queue
        assert service.transcript_wait_time == 0.5

    def test_build_deepgram_url(self, service):
        """Test DeepGram URL building"""
        url = service.build_deepgram_url()
        
        assert 'wss://api.deepgram.com/v1/listen' in url
        assert 'encoding=linear16' in url
        assert 'sample_rate=16000' in url
        assert 'channels=1' in url
        assert 'punctuate=true' in url
        assert 'interim_results=true' in url

    @pytest.mark.asyncio
    async def test_connect_to_deepgram_success(self, service):
        """Test successful DeepGram connection"""
        with patch('audio_service.websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            result = await service.initialize_deepgram()
            
            assert result is True
            assert service.deepgram_ws == mock_websocket

    @pytest.mark.asyncio
    async def test_connect_to_deepgram_failure(self, service):
        """Test failed DeepGram connection"""
        with patch('audio_service.websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = await service.initialize_deepgram()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_send_audio_data(self, service, mock_websocket):
        """Test sending audio data to DeepGram"""
        service.deepgram_ws = mock_websocket
        
        # Create test audio data
        audio_data = b"test audio bytes"
        
        await service.send_audio(audio_data)
        
        # Verify audio was sent
        mock_websocket.send.assert_called_once_with(audio_data)

    @pytest.mark.asyncio
    async def test_send_audio_data_not_connected(self, service):
        """Test sending audio data when not connected"""
        service.deepgram_ws = None
        
        audio_data = b"test audio bytes"
        
        result = await service.send_audio(audio_data)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_control_message(self, service, mock_websocket):
        """Test sending control message to DeepGram"""
        service.deepgram_ws = mock_websocket
        
        control_data = {"type": "CloseStream"}
        await service.send_control(control_data)
        
        mock_websocket.send.assert_called_once()
        sent_data = mock_websocket.send.call_args[0][0]
        print(sent_data)
        assert '{"type": "CloseStream"}' == sent_data

    @pytest.mark.asyncio
    async def test_send_keepalive_message(self, service, mock_websocket):
        """Test sending keepalive message to DeepGram"""
        service.deepgram_ws = mock_websocket
        
        # Start keepalive task
        task = asyncio.create_task(service.send_keepalive())
        
        # Wait a bit for the task to run
        await asyncio.sleep(10)
        
        # Cancel the task
        task.cancel()
        
        # Verify keepalive was sent
        mock_websocket.send.assert_called()
        sent_calls = mock_websocket.send.call_args_list
        assert any('{"type": "KeepAlive"}' in call[0][0] for call in sent_calls)

    @pytest.mark.asyncio
    async def test_handle_message_audio(self, service):
        """Test handling audio message"""
        with patch.object(service, 'send_audio', new_callable=AsyncMock) as mock_send:
            audio_data = "dGVzdCBhdWRpbyBkYXRh"  # base64 encoded "test audio data"
            message = json.dumps({
                "type": "audio",
                "data": audio_data
            })
            
            await service.handle_message(message)
            
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_control(self, service):
        """Test handling control message"""
        with patch.object(service, 'send_control', new_callable=AsyncMock) as mock_send:
            control_data = {"type": "Finalize"}
            message = json.dumps({
                "type": "control",
                "data": control_data
            })
            
            await service.handle_message(message)
            
            mock_send.assert_called_once_with(control_data)

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self, service):
        """Test handling invalid JSON message"""
        invalid_message = "invalid json"
        
        # Should not raise an exception
        await service.handle_message(invalid_message)

    @pytest.mark.asyncio
    async def test_get_transcript(self, service, transcript_queue):
        """Test getting transcripts from queue"""
        test_transcript = "Hello world"
        
        # Put transcript directly in queue
        await transcript_queue.put({"transcript": test_transcript})
        
        # Get transcript
        queue_item = await service.get_transcript()
        
        assert queue_item["transcript"] == test_transcript

    @pytest.mark.asyncio
    async def test_listen_for_transcripts_success(self, service):
        """Test successful transcript listening"""
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__.return_value = [
            json.dumps({
                "channel": {
                    "alternatives": [{
                        "transcript": "Test transcript"
                    }]
                },
                "is_final": True,
                "speech_final": True
            })
        ]
        
        service.deepgram_ws = mock_websocket
        
        # Run for a short time to process the message
        try:
            await asyncio.wait_for(service.listen_for_transcripts(), timeout=0.1)
        except asyncio.TimeoutError:
            pass  # Expected timeout

    @pytest.mark.asyncio
    async def test_listen_for_transcripts_not_connected(self, service):
        """Test transcript listening when not connected"""
        service.deepgram_ws = None
        
        # Should not raise an exception
        await service.listen_for_transcripts()

    @pytest.mark.asyncio
    async def test_initialize_success(self, service):
        """Test successful service initialization"""
        with patch.object(service, 'initialize_deepgram', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True
            
            result = await service.initialize()
            
            assert result is True

    @pytest.mark.asyncio
    async def test_initialize_deepgram_failure(self, service):
        """Test failed service initialization"""
        with patch.object(service, 'initialize_deepgram', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = False
            
            result = await service.initialize()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_close_service(self, service, mock_websocket):
        """Test closing the service"""
        service.deepgram_ws = mock_websocket
        
        await service.close()
        
        mock_websocket.send.assert_called_once()
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_service_not_connected(self, service):
        """Test closing service when not connected"""
        service.deepgram_ws = None
        
        # Should not raise an exception
        await service.close()

    def test_get_transcript_queue(self, service, transcript_queue):
        """Test getting the transcript queue"""
        assert service.transcript_queue == transcript_queue

    @pytest.mark.asyncio
    async def test_adjust_timestamps(self, service):
        """Test timestamp adjustment"""
        # Set speech start timestamp
        service.speech_start_timestamp = 1000.0
        
        # Create test response
        response = {
            "start": 1.0,
            "channel": {
                "alternatives": [{
                    "words": [
                        {
                            "word": "hello",
                            "start": 1.5,
                            "end": 2.0
                        }
                    ]
                }]
            }
        }
        
        adjusted_response = service.adjust_timestamps(response)
        
        assert adjusted_response["start"] == 1001.0
        assert adjusted_response["channel"]["alternatives"][0]["words"][0]["start"] == 1001.5
        assert adjusted_response["channel"]["alternatives"][0]["words"][0]["end"] == 1002.0
        assert "retrieval_time" in adjusted_response

    @pytest.mark.asyncio
    async def test_adjust_timestamps_no_speech_start(self, service):
        """Test timestamp adjustment when no speech start timestamp"""
        response = {
            "start": 1.0,
            "channel": {
                "alternatives": [{
                    "words": [
                        {
                            "word": "hello",
                            "start": 1.5,
                            "end": 2.0
                        }
                    ]
                }]
            }
        }
        
        adjusted_response = service.adjust_timestamps(response)
        
        # Should return unchanged response
        assert adjusted_response == response


if __name__ == "__main__":
    pytest.main([__file__]) 