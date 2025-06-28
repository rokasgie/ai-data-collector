# Voice Chat System with DeepGram STT and OpenAI Integration

A real-time voice chat system with a Python WebSocket backend for speech-to-text transcription using DeepGram and AI responses using OpenAI, plus a modern Next.js web frontend.

## Features

- **Real-time Voice Chat**: Web-based voice chat with real-time transcription
- **DeepGram STT Integration**: High-quality speech-to-text transcription with punctuation
- **OpenAI Integration**: AI-powered responses with streaming capabilities
- **Modern Web UI**: Beautiful, responsive Next.js frontend with real-time updates
- **Voice Activity Detection**: Automatic speech detection and processing
- **Audio Playback**: Record, play, and manage audio clips
- **Multi-client Support**: Handle multiple users simultaneously

## Architecture

```
Web Client (Next.js) → WebSocket Server (Python) → DeepGram STT → OpenAI → Web Client
```

1. **Web Client**: Captures audio, displays transcripts, and shows AI responses
2. **WebSocket Server**: Manages connections and coordinates between services
3. **DeepGram STT**: Performs real-time speech recognition with punctuation
4. **OpenAI**: Generates AI responses based on user transcripts
5. **Audio Service**: Handles audio streaming and transcript processing

## Prerequisites

- **Python 3.8+** for the backend
- **Node.js 18+** for the frontend
- **DeepGram API Key** for speech-to-text
- **OpenAI API Key** for AI responses

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd caller
```

### 2. Environment Configuration

Copy the example environment file and configure your API keys:

```bash
cp env.example .env
```

Edit `.env` with your API keys:

```env
# DeepGram API Key (Required)
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# OpenAI API Key (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration (Optional)
SERVER_HOST=localhost
SERVER_PORT=8765
```

### 3. Install Dependencies

#### Backend Dependencies

```bash
pip install -r requirements.txt
```

#### Frontend Dependencies

```bash
cd web-client
npm install
```

### 4. Launch the System

#### Start the Backend Server

In the root directory:

```bash
python server.py
```

You should see output like:
```
🚀 Starting MainServer at ws://localhost:8765
✅ AudioService initialized
✅ MainServer is running
```

#### Start the Frontend

In a new terminal, navigate to the web-client directory:

```bash
cd web-client
npm run dev
```

You should see output like:
```
- ready started server on 0.0.0.0:3000, url: http://localhost:3000
```

### 5. Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:3000
- **Backend WebSocket**: ws://localhost:8765

## Detailed Setup Instructions

### API Keys Setup

#### DeepGram API Key

1. Go to [DeepGram Console](https://console.deepgram.com/)
2. Sign up or log in to your account
3. Navigate to the API Keys section
4. Create a new API key or copy an existing one
5. Add it to your `.env` file as `DEEPGRAM_API_KEY`

#### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Add it to your `.env` file as `OPENAI_API_KEY`

### Backend Setup

The backend consists of several Python services:

#### Main Server (`server.py`)
- WebSocket server for client connections
- Coordinates between audio service and OpenAI service
- Handles transcript processing and AI responses

#### Audio Service (`audio_service.py`)
- Manages DeepGram WebSocket connection
- Processes real-time audio streams
- Handles transcript timing and adjustments

#### OpenAI Service (`openai_service.py`)
- Manages OpenAI API communication
- Handles conversation history
- Streams AI responses back to clients

### Frontend Setup

The frontend is a Next.js application with:

#### Key Features
- Real-time audio recording and playback
- Voice Activity Detection (VAD)
- WebSocket communication with backend
- Real-time transcript display
- AI response streaming

#### Technologies Used
- **Next.js 15**: React framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **WebSocket**: Real-time communication
- **Web Audio API**: Audio processing

## Usage

### Using the Voice Chat

1. **Open the Application**: Navigate to http://localhost:3000
2. **Grant Microphone Permission**: Allow the browser to access your microphone
3. **Start Speaking**: The system will automatically detect your voice and transcribe it
4. **View Transcripts**: Your speech will appear in real-time as you speak
5. **Receive AI Responses**: The AI will respond to your messages automatically

### Voice Activity Detection

The system uses advanced Voice Activity Detection (VAD) to:
- Automatically detect when you start speaking
- Determine when you've finished speaking
- Process only speech segments (not silence)
- Provide real-time feedback

### Audio Controls

- **Record**: Click to start recording audio
- **Play**: Play back recorded audio clips
- **Stop**: Stop current recording or playback
- **Clear**: Remove recorded audio clips

## Configuration

### Backend Configuration

#### Environment Variables

```env
# Required
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key

# Optional
SERVER_HOST=localhost
SERVER_PORT=8765
DG_SAMPLE_RATE=16000
DG_CHANNELS=1
DG_ENCODING=linear16
```

#### DeepGram Parameters

The system is configured for optimal performance with:
- **Sample Rate**: 16kHz (high quality)
- **Channels**: 1 (mono)
- **Encoding**: Linear16
- **Punctuation**: Enabled
- **Interim Results**: Enabled

### Frontend Configuration

The frontend automatically connects to the backend WebSocket server. Configuration is handled through:

- **WebSocket URL**: Automatically connects to `ws://localhost:8765`
- **Audio Settings**: Optimized for voice chat
- **VAD Settings**: Configured for natural speech detection

## Development

### Project Structure

```
caller/
├── server.py                 # Main WebSocket server
├── audio_service.py          # DeepGram audio processing
├── openai_service.py         # OpenAI integration
├── call_info.py              # Data models
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── env.example              # Environment template
├── tests/                    # Test suite
│   ├── test_audio_service.py
│   └── test_openai_service.py
├── web-client/               # Next.js frontend
│   ├── src/
│   │   └── app/
│   ├── package.json
│   └── README.md
└── README.md                 # This file
```

### Running Tests

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Run all tests
cd tests
python -m pytest

# Run specific test files
python -m pytest test_audio_service.py -v
python -m pytest test_openai_service.py -v
```

### Development Mode

#### Backend Development

```bash
# Run with debug logging
python server.py

# Monitor logs for debugging
tail -f server.log
```

#### Frontend Development

```bash
cd web-client
npm run dev
```

The frontend will hot-reload on changes.

## Troubleshooting

### Common Issues

#### Backend Issues

1. **DeepGram Connection Failed**
   - Verify `DEEPGRAM_API_KEY` is set correctly
   - Check internet connection
   - Ensure DeepGram account has sufficient credits

2. **OpenAI Connection Failed**
   - Verify `OPENAI_API_KEY` is set correctly
   - Check OpenAI account has sufficient credits
   - Ensure API key has proper permissions

3. **Port Already in Use**
   - Change `SERVER_PORT` in `.env`
   - Kill existing processes using the port

#### Frontend Issues

1. **Microphone Not Working**
   - Check browser permissions
   - Ensure HTTPS in production (required for microphone access)
   - Try refreshing the page

2. **WebSocket Connection Failed**
   - Verify backend server is running
   - Check WebSocket URL in browser console
   - Ensure no firewall blocking the connection

3. **Audio Not Playing**
   - Check browser audio settings
   - Ensure audio files are properly loaded
   - Try different browser

### Debug Mode

#### Backend Debug

Enable debug logging by modifying the logging level:

```python
# In server.py, audio_service.py, or openai_service.py
logging.basicConfig(level=logging.DEBUG)
```

#### Frontend Debug

Open browser developer tools (F12) and check:
- Console for JavaScript errors
- Network tab for WebSocket connections
- Application tab for audio permissions

### Logs

The system provides comprehensive logging:

- **Backend**: Console output with emoji indicators
- **Frontend**: Browser console and network tab
- **WebSocket**: Real-time connection status

## Deployment

### Production Setup

#### Backend Deployment

1. **Environment Variables**: Set production API keys
2. **HTTPS**: Use SSL certificates for secure WebSocket connections
3. **Process Management**: Use PM2 or similar for process management
4. **Load Balancing**: Consider multiple server instances

#### Frontend Deployment

1. **Build**: `npm run build`
2. **Deploy**: Use Vercel, Netlify, or your preferred hosting
3. **Environment**: Set production WebSocket URL
4. **HTTPS**: Required for microphone access

### Docker Deployment

```dockerfile
# Backend Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "server.py"]
```

## API Reference

### WebSocket Messages

#### Client to Server

```json
{
  "type": "audio",
  "data": "base64_encoded_audio",
  "startTime": 1234567890
}
```

#### Server to Client

```json
{
  "type": "turn",
  "data": {
    "role": "user|assistant",
    "content": "transcript or response text"
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source and available under the MIT License. 