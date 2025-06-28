# Voice Chat System with DeepGram STT, OpenAI and ElevenLabs Integration

A real-time voice chat system with a Python WebSocket backend for speech-to-text transcription using DeepGram and AI responses using OpenAI, plus a modern Next.js web frontend.

## Architecture

```
Web Client (Next.js) → WebSocket Server (Python) → DeepGram STT → OpenAI → Web Client
```

1. **Web Client**: Captures audio, displays transcripts, and shows AI responses, as well as synthesizes audio. Using a separate frontend client was chosen to simplify debugging processes and create a separation of concerns - backend does audio and LLM processing while frontend performns lighter tasks, such as VAD and voice synthesis. In the future it would also be easier to implement interruptions using this system as the voice synthesis and VAD are both hosted in the frontend.
2. **WebSocket Server**: Manages connections and coordinates between services. This is used as a router between different services. The main complexity here stems from the DeepGram STT API where late transcriptions and other errors need to be handled. It uses websockets to communicate with the web client.
It runs a periodic task to check the transcription queue and decides whether to send data back to the web client and OpenAI service.
3. **Audio Service**: Handles audio streaming and transcript processing from DeepGram. It uses websockets to connect with DeepGram and tracks timestamps of incoming audio.
4. **OpenAI**: Generates AI responses based on user transcripts. It implements an agentic approach to parse and check what information is still missing and what should be asked next. It utilizes OpenAI's parsing and chat completion endpoint and stores internal call state in memory. It sends data back to the client in sentences to reduce the delay between response generation and synthesis start.

## Improvements

1. The main imprivement is to configure the VAD + STT pipeline to run smoother together - sometimes audio is missed and sometimes DeepGram returns multiple transcriptions and does not work deterministaclly all the time. More time should be spent on working with DeepGram API to figure this out as this is currently the biggest source of latency in the pipeline
2. Using Redis or other messaging systems to store states (for example call state) and support multiple clients - currently system stores everything in memory and only supports a single client
3. Setting up a proper OpenAI agent with more diverse scenarions and more natrual sounding speech.
4. Error handling, websocket closure and restart processes.

## Quick Start

### 1. Environment Configuration

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

#### Frontend Environment Variables

For the Next.js frontend, create a `.env.local` file in the `web-client` directory:

```bash
cd web-client
cp .env.example .env.local
```

Edit `web-client/.env.local` with your ElevenLabs API key:

```env
# ElevenLabs API Key (Required for text-to-speech)
NEXT_PUBLIC_ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Backend WebSocket URL (Optional - defaults to localhost)
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8765
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

### Backend Setup

The backend consists of several Python services:

#### Main Server (`server.py`)
- WebSocket server for client connections
- Coordinates between audio service and OpenAI service
- Handles transcript processing and AI responses
- Deals with Deepgram late trasncriptions issues

#### Audio Service (`audio_service.py`)
- Manages DeepGram WebSocket connection
- Processes real-time audio streams
- Handles transcript timing and adjustments

#### OpenAI Service (`openai_service.py`)
- Manages OpenAI API communication
- Handles conversation history
- Performs agentic data collection scenario
- Streams AI responses back to clients

### Frontend Setup

The frontend is a Next.js application with:

#### Key Features
- Real-time audio recording and playback
- Voice Activity Detection (VAD)
- WebSocket communication with backend
- Real-time transcript display
- AI response streaming and voice synthesis

## Usage

### Using the Voice Chat

1. **Open the Application**: Navigate to http://localhost:3000
2. **Grant Microphone Permission**: Allow the browser to access your microphone
3. **Start Speaking**: The system will automatically detect your voice and transcribe it
4. **View Transcripts**: Your speech will appear in real-time as you speak
5. **Receive AI Responses**: The AI will respond to your messages automatically
