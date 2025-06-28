import asyncio
import websockets
import pyaudio
import wave
import logging
import argparse
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioClient:
    def __init__(self, server_url='ws://localhost:8765'):
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        
        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 8000
        
        # PyAudio instance
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.file_stream = None
        
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info(f"Connected to server at {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from server")
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.file_stream:
            self.file_stream.close()
        
        if self.audio:
            self.audio.terminate()
    
    def start_microphone_stream(self):
        """Start capturing audio from microphone"""
        try:
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            logger.info("Microphone audio stream started")
            return True
        except Exception as e:
            logger.error(f"Failed to start microphone stream: {e}")
            return False
    
    def start_file_stream(self, filename):
        """Start streaming audio from file"""
        try:
            if not os.path.exists(filename):
                logger.error(f"File not found: {filename}")
                return False
            
            self.file_stream = wave.open(filename, 'rb')
            
            # Check if file format matches our requirements
            if self.file_stream.getnchannels() != self.CHANNELS:
                logger.warning(f"File has {self.file_stream.getnchannels()} channels, converting to mono")
            
            if self.file_stream.getframerate() != self.RATE:
                logger.warning(f"File sample rate is {self.file_stream.getframerate()}Hz, expected {self.RATE}Hz")
            
            logger.info(f"File audio stream started: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to start file stream: {e}")
            return False
    
    async def send_microphone_audio(self):
        """Send audio data from microphone to server"""
        if not self.connected or not self.stream:
            logger.error("Not connected or microphone stream not started")
            return
        
        logger.info("Started sending microphone audio to server...")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.connected:
                # Read audio data from microphone
                audio_data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                
                # Send audio data to server
                if self.websocket and self.connected:
                    await self.websocket.send(audio_data)
                
                # Small delay to prevent overwhelming the server
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error sending microphone audio: {e}")
    
    async def send_file_audio(self):
        """Send audio data from file to server"""
        if not self.connected or not self.file_stream:
            logger.error("Not connected or file stream not started")
            return
        
        logger.info("Started sending file audio to server...")
        
        try:
            while self.connected:
                # Read audio data from file
                audio_data = self.file_stream.readframes(self.CHUNK)
                
                # Check if we've reached the end of the file
                if not audio_data:
                    logger.info("Reached end of audio file")
                    break
                
                # Send audio data to server
                if self.websocket and self.connected:
                    await self.websocket.send(audio_data)
                
                # Small delay to simulate real-time streaming
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error sending file audio: {e}")
    
    async def send_command(self, command):
        """Send a command to the server"""
        if not self.connected:
            logger.error("Not connected to server")
            return
        
        try:
            message = json.dumps({'command': command})
            await self.websocket.send(message)
            logger.info(f"Sent command: {command}")
        except Exception as e:
            logger.error(f"Error sending command: {e}")
    
    async def handle_server_message(self, message):
        """Handle messages from server"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
                
                # Handle status messages
                if data.get('status'):
                    status = data.get('status')
                    if status == 'recording_started':
                        logger.info("📹 Recording started")
                    elif status == 'recording_stopped':
                        chunks = data.get('chunks', 0)
                        logger.info(f"📹 Recording stopped. Total chunks: {chunks}")
                    elif status == 'audio_saved':
                        filename = data.get('filename', 'unknown')
                        logger.info(f"💾 Audio saved to: {filename}")
                    elif status == 'pong':
                        timestamp = data.get('timestamp', 'unknown')
                        logger.info(f"🏓 Server ping response at: {timestamp}")
                    elif status == 'error':
                        error_msg = data.get('message', 'Unknown error')
                        logger.error(f"❌ Server error: {error_msg}")
                        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from server: {message}")
        except Exception as e:
            logger.error(f"Error handling server message: {e}")
    
    async def receive_messages(self):
        """Receive and handle messages from server"""
        if not self.connected:
            return
        
        try:
            async for message in self.websocket:
                await self.handle_server_message(message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to server closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            self.connected = False
    
    async def run(self, audio_source=None):
        """Main client loop"""
        if not await self.connect():
            return
        
        # Start receiving messages in background
        receive_task = asyncio.create_task(self.receive_messages())
        
        try:
            if audio_source and os.path.exists(audio_source):
                # Stream from file
                if not self.start_file_stream(audio_source):
                    await self.disconnect()
                    return
                await self.send_file_audio()
            else:
                # Stream from microphone
                if not self.start_microphone_stream():
                    await self.disconnect()
                    return
                await self.send_microphone_audio()
        
        except KeyboardInterrupt:
            logger.info("Client stopped by user")
        
        finally:
            receive_task.cancel()
            await self.disconnect()

async def main():
    """Main function to run the client"""
    parser = argparse.ArgumentParser(description='WebSocket Audio Streaming Client')
    parser.add_argument('--file', '-f', type=str, help='Audio file to stream (WAV format)')
    parser.add_argument('--server', '-s', type=str, default='ws://localhost:8765', 
                       help='WebSocket server URL (default: ws://localhost:8765)')
    
    args = parser.parse_args()
    
    client = AudioClient(args.server)
    await client.run(args.file)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Client error: {e}") 