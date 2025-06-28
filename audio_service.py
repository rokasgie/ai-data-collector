import asyncio
import websockets
import json
import logging
import os
from urllib.parse import urlencode
from dotenv import load_dotenv
import base64
from datetime import datetime
import time

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AudioService")

class AudioService:
    def __init__(self, transcript_queue: asyncio.Queue, transcript_wait_time: float):
        self.transcript_wait_time = transcript_wait_time
        self.deepgram_ws = None
        self.transcript_queue = transcript_queue
        self.speech_start_timestamp = None
        self.last_audio_start_time = None

    def build_deepgram_url(self):
        base_url = "wss://api.deepgram.com/v1/listen"
        params = {
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1",
            "punctuate": "true",
            "interim_results": "true"
        }
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    async def send_keepalive(self):
        """Send keepalive messages to DeepGram every 9 seconds"""
        while True:
            try:
                await asyncio.sleep(9)  # Wait 9 seconds
                if self.deepgram_ws:
                    await self.deepgram_ws.send(json.dumps({"type": "KeepAlive"}))
                    logger.debug("📤 Sent KeepAlive to DeepGram")
            except Exception as e:
                logger.error(f"Error sending KeepAlive: {e}")
                break

    async def get_transcript(self):
        """Get a transcript from the queue"""
        return await self.transcript_queue.get()

    async def initialize(self):
        """Initialize the AudioService with DeepGram connection and start background tasks"""
        if not await self.initialize_deepgram():
            logger.error("❌ Failed to initialize AudioService")
            return False
        
        # Start keepalive task
        asyncio.create_task(self.send_keepalive())
        
        # Start transcript listener
        asyncio.create_task(self.listen_for_transcripts())
        
        logger.info("✅ AudioService initialized")
        return True

    async def initialize_deepgram(self):
        """Initialize connection to DeepGram"""
        dg_url = self.build_deepgram_url()
        dg_api_key = os.getenv("DEEPGRAM_API_KEY")
        if not dg_api_key:
            logger.error("Missing DEEPGRAM_API_KEY in environment")
            return False

        try:
            self.deepgram_ws = await websockets.connect(
                dg_url,
                additional_headers={"Authorization": f"Token {dg_api_key}"}
            )
            logger.info("🟢 Connected to Deepgram")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to DeepGram: {e}")
            return False

    async def send_audio(self, audio_data: bytes):
        """Send audio data to DeepGram"""
        if not self.deepgram_ws:
            logger.error("❌ Not connected to DeepGram")
            return False
        
        try:
            await self.deepgram_ws.send(audio_data)
            logger.debug(f"📤 Sent audio to DeepGram: {len(audio_data)} bytes")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending audio to DeepGram: {e}")
            return False

    async def send_control(self, control_data: dict):
        """Send control message to DeepGram"""
        if not self.deepgram_ws:
            logger.error("❌ Not connected to DeepGram")
            return False
        
        try:
            await self.deepgram_ws.send(json.dumps(control_data))
            logger.info(f"📤 Sent control to DeepGram: {control_data}")
            return True
        except Exception as e:
            logger.error(f"❌ Error sending control to DeepGram: {e}")
            return False

    async def handle_message(self, message: str):
        """Handle structured message from client"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "audio":
                audio_data = data.get("data")
                start_time = data.get("startTime")
                
                if audio_data:
                    audio_bytes = base64.b64decode(audio_data)
                    await self.send_audio(audio_bytes)
                    logger.debug(f"📤 Processed audio message: {len(audio_bytes)} bytes")
                    
                    # Store the speech start timestamp once and never overwrite it
                    if start_time and self.speech_start_timestamp is None:
                        self.speech_start_timestamp = start_time
                        logger.info(f"🎤 Speech start timestamp recorded once: {start_time}")
                    
                    # Always update the last audio start time
                    if start_time:
                        self.last_audio_start_time = start_time
                        logger.debug(f"🎤 Last audio start time updated: {start_time}")
                else:
                    logger.warning("Audio message missing data")
                    
            elif message_type == "control":
                control_data = data.get("data", {})
                await self.send_control(control_data)
                logger.debug(f"📤 Processed control message: {control_data}")
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def adjust_timestamps(self, response):
        """Adjust timestamps for the response and all words using the speech start timestamp"""
        if self.speech_start_timestamp is None:
            return response
        
        epoch_start_time = self.speech_start_timestamp
        
        # Add response retrieval time
        response["retrieval_time"] = time.time()
        
        # Adjust the overall start time
        original_start = response.get("start", 0)
        response["start"] = original_start + epoch_start_time
        logger.debug(f"🕐 Adjusted response start time: {original_start} -> {response['start']}")
        
        # Adjust timestamps for each word in the response
        try:
            alternatives = response.get("channel", {}).get("alternatives", [])
            if alternatives and len(alternatives) > 0:
                words = alternatives[0].get("words", [])
                for word in words:
                    if "start" in word:
                        original_word_start = word["start"]
                        word["start"] = original_word_start + epoch_start_time
                        logger.debug(f"🕐 Adjusted word '{word.get('word', '')}' start: {original_word_start} -> {word['start']}")
                    
                    if "end" in word:
                        original_word_end = word["end"]
                        word["end"] = original_word_end + epoch_start_time
                        logger.debug(f"🕐 Adjusted word '{word.get('word', '')}' end: {original_word_end} -> {word['end']}")
        except Exception as e:
            logger.error(f"Error adjusting word timestamps: {e}")
        
        return response

    async def listen_for_transcripts(self):
        """Listen for transcripts from DeepGram and put them in queue"""
        if not self.deepgram_ws:
            logger.error("❌ Not connected to DeepGram")
            return
        
        try:
            async for msg in self.deepgram_ws:
                try:
                    response = json.loads(msg)
                    
                    transcript = (
                        response.get("channel", {})
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                    )
                    is_final = response.get("is_final", False)
                    
                    if transcript and is_final:
                        logger.info(f"📤 Received transcript from DeepGram: {response}")
                        response = self.adjust_timestamps(response)
                        
                        if self.last_audio_start_time and "retrieval_time" in response:
                            time_diff = response["retrieval_time"] - self.last_audio_start_time
                            if time_diff > self.transcript_wait_time:
                                logger.warning(f"⏰ Skipping transcript - time difference too large: {time_diff:.3f}s > 0.5s")
                                continue
                            else:
                                logger.debug(f"⏰ Time difference acceptable: {time_diff:.3f}s")
                        
                        await self.transcript_queue.put(response)
                except Exception as e:
                    logger.warning(f"Failed to parse Deepgram response: {e}. Raw message: {msg}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram connection closed")
        except Exception as e:
            logger.error(f"Error receiving from Deepgram: {e}")

    async def close(self):
        """Close the DeepGram connection"""
        if self.deepgram_ws:
            try:
                await self.deepgram_ws.send(json.dumps({"type": "CloseStream"}))
                await self.deepgram_ws.close()
                logger.info("🔴 Closed DeepGram connection")
            except Exception as e:
                logger.error(f"Error closing DeepGram connection: {e}")
            finally:
                self.deepgram_ws = None 