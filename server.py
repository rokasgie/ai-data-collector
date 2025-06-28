import asyncio
from asyncio import QueueEmpty
import websockets
import json
import logging
import os
import time
import re
from audio_service import AudioService
from openai_service import OpenAIService
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MainServer")

class MainServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.transcript_queue = asyncio.Queue()
        self.transcript_wait_time = 0.5
        self.audio_service = AudioService(self.transcript_queue, self.transcript_wait_time)

        self.openai_service = OpenAIService()

        self.web_client = None
        self.periodic_task = None
        

    def parse_response(self, response):
        try:
            alternatives = response.get("channel", {}).get("alternatives", [])
            if alternatives and len(alternatives) > 0:
                return alternatives[0].get("transcript", "")
            else:
                logger.warning("🔤 No alternatives found in DeepGram response")
                return ""
                
        except Exception as e:
            logger.error(f"Error parsing DeepGram response: {e}")
            return ""

    async def process_transcripts_periodically(self):
        logger.info("🔄 Starting periodic transcript processor")
        while True:
            try:
                await asyncio.sleep(0.1)
                
                # Process all transcripts from the queue
                latest_response = None
                current_time = time.time()
                
                while not self.transcript_queue.empty():
                    try:
                        latest_response = self.transcript_queue.get_nowait()
                    except QueueEmpty:
                        break
                
                if not latest_response:
                    continue
                
                retrieval_time = latest_response.get("retrieval_time", 0)
                time_since_latest = current_time - retrieval_time
                
                logger.info(f"🔄 Latest transcript retrieved {time_since_latest:.2f}s ago")
                
                if time_since_latest <= self.transcript_wait_time:
                    transcript = self.parse_response(latest_response)
                    
                    # Send the transcript to client and OpenAI
                    await self.send_transcripts_to_client(transcript)
                    await self.send_words_to_openai(transcript)
                
            except Exception as e:
                logger.error(f"❌ Error in periodic transcript processing: {e}")

    async def send_transcripts_to_client(self, transcript: str):
        if not self.web_client:
            logger.debug("📤 No web client, skipping send to client")
            return
        
        user_message = json.dumps({
            "type": "turn", 
            "data": {
                "role": "user",
                "content": transcript
            }
        })
        
        try:
            await self.web_client.send(user_message)
            logger.info(f"✅ Sent transcript to web client: '{transcript}'")
            
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔴 Web client disconnected during transcript send")
            self.web_client = None
        except Exception as e:
            logger.error(f"Error sending transcript to web client: {e}")
            self.web_client = None

    async def send_words_to_openai(self, transcript: str):
        """Send transcript to OpenAI for AI responses"""
        if not self.web_client:
            logger.debug("🤖 No web client, returning early")
            return
        
        if not transcript.strip():
            logger.debug("🤖 No transcript to send to OpenAI")
            return
        
        logger.info(f"🤖 Sending transcript to OpenAI: '{transcript}'")
        
        try:
            # Define callback function to send AI responses sentence by sentence
            async def send_ai_response(sentence: str):
                if self.web_client:
                    ai_message = json.dumps({
                        "type": "turn", 
                        "data": {
                            "role": "assistant",
                            "content": sentence
                        }
                    })
                    await self.web_client.send(ai_message)
                    logger.info(f"🤖 Sent AI response: '{sentence}'")
            
            logger.info("🤖 Calling OpenAI service...")
            await self.openai_service.send_to_openai(transcript, send_ai_response)
            logger.info("🤖 OpenAI service call completed")
            
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔴 Web client disconnected during OpenAI processing")
            self.web_client = None
        except Exception as e:
            logger.error(f"Error sending transcript to OpenAI: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.web_client = None

    async def handle_client(self, websocket):
        """Handle web client connection"""
        if self.web_client:
            logger.warning("🔴 Another web client is already connected. Rejecting new connection.")
            await websocket.close()
            return
            
        logger.info("🔵 New web client connected")
        self.web_client = websocket

        try:
            async for message in websocket:
                if isinstance(message, str):
                    await self.audio_service.handle_message(message)
                else:
                    logger.warning(f"Unexpected message format from web client: {type(message)}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("🔴 Web client disconnected")
        except Exception as e:
            logger.error(f"❌ Error with web client: {e}")
        finally:
            self.web_client = None

    async def start(self):
        """Start the main server"""
        logger.info(f"🚀 Starting MainServer at ws://{self.host}:{self.port}")
        
        # Initialize AudioService
        if not await self.audio_service.initialize():
            logger.error("❌ Failed to initialize AudioService. Exiting.")
            return

        self.periodic_task = asyncio.create_task(self.process_transcripts_periodically())
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info("✅ MainServer is running")
            await asyncio.Future()

    async def stop(self):
        """Stop the server and cleanup"""
        logger.info("🛑 Stopping MainServer")
        if self.periodic_task and not self.periodic_task.done():
            self.periodic_task.cancel()
        if self.web_client:
            await self.web_client.close()
        await self.audio_service.close()


if __name__ == "__main__":
    server = MainServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        asyncio.run(server.stop())
