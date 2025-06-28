'use client';

import { useState, useRef, useEffect } from 'react';
import { ElevenLabsClient, play } from '@elevenlabs/elevenlabs-js';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AudioClip {
  id: string;
  timestamp: Date;
  audioData: Float32Array;
  duration: number;
  isPlaying: boolean;
}

// Declare global vad object
declare global {
  interface Window {
    vad: any;
  }
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStarted, setIsStarted] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [hasVoiceActivity, setHasVoiceActivity] = useState(false);
  const [audioClips, setAudioClips] = useState<AudioClip[]>([]);
  const [showAudioPanel, setShowAudioPanel] = useState(false);
  
  const websocketRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isProcessingSpeechEnd = useRef<boolean>(false);
  const elevenlabsRef = useRef<ElevenLabsClient | null>(null);
  const voiceQueue = useRef<string[]>([]);
  const isPlayingVoice = useRef<boolean>(false);
  const vadInstanceRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const speechStartTimeRef = useRef<number | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize ElevenLabs client
  useEffect(() => {
    elevenlabsRef.current = new ElevenLabsClient({
      apiKey: process.env.NEXT_PUBLIC_ELEVEN_LABS_API_KEY || ''
    });
  }, []);

  const addOrUpdateAssistantMessage = (content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const synthesizeAndPlaySpeech = async (text: string) => {
    // Add text to queue
    voiceQueue.current.push(text);
    
    // If not currently playing, start processing the queue
    if (!isPlayingVoice.current) {
      processVoiceQueue();
    }
  };

  const processVoiceQueue = async () => {
    if (voiceQueue.current.length === 0 || isPlayingVoice.current) {
      return;
    }

    isPlayingVoice.current = true;
    const text = voiceQueue.current.shift()!;

    try {
      if (!elevenlabsRef.current) {
        console.error('❌ ElevenLabs client not initialized');
        isPlayingVoice.current = false;
        // Continue processing queue
        processVoiceQueue();
        return;
      }

      console.log('🎵 Starting streaming synthesis for:', text);
      
      const audioStream = await elevenlabsRef.current.textToSpeech.stream('JBFqnCBsd6RMkjVDRZzb', {
        modelId: 'eleven_flash_v2_5',
        text,
        outputFormat: 'mp3_44100_128',
        languageCode: 'en',
        voiceSettings: {
          stability: 0,
          similarityBoost: 1.0,
          useSpeakerBoost: true,
          speed: 1.0,
        },
      });

      // Create MediaSource for streaming playback
      const mediaSource = new MediaSource();
      const audioUrl = URL.createObjectURL(mediaSource);
      const audioElement = new Audio(audioUrl);
      
      // Set up event handlers
      audioElement.onended = () => {
        URL.revokeObjectURL(audioUrl);
        isPlayingVoice.current = false;
        console.log('✅ Streaming speech finished, processing next in queue');
        // Process next item in queue
        processVoiceQueue();
      };

      audioElement.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        isPlayingVoice.current = false;
        console.error('❌ Error playing streaming audio, processing next in queue');
        // Process next item in queue
        processVoiceQueue();
      };

      mediaSource.addEventListener('sourceopen', async () => {
        try {
          const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
          const reader = audioStream.getReader();
          
          console.log('🎵 Starting streaming playback');
          
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            // Wait for source buffer to be ready
            if (sourceBuffer.updating) {
              await new Promise<void>((resolve) => {
                sourceBuffer.addEventListener('updateend', () => resolve(), { once: true });
              });
            }
            
            // Append chunk to source buffer for immediate playback
            sourceBuffer.appendBuffer(value);
          }
          
          // Wait for final update to complete before ending stream
          if (sourceBuffer.updating) {
            await new Promise<void>((resolve) => {
              sourceBuffer.addEventListener('updateend', () => resolve(), { once: true });
            });
          }
          
          // Check if media source is still open before ending stream
          if (mediaSource.readyState === 'open') {
            mediaSource.endOfStream();
            console.log('✅ Streaming synthesis completed');
          }
          
        } catch (error) {
          console.error('❌ Error in streaming playback:', error);
          // Only call endOfStream if media source is still open
          if (mediaSource.readyState === 'open') {
            try {
              mediaSource.endOfStream();
            } catch (endError) {
              console.error('❌ Error ending stream:', endError);
            }
          }
        }
      });
      
      // Start playing as soon as possible
      await audioElement.play();
      console.log('✅ Streaming audio started playing');
      
    } catch (error) {
      console.error('❌ Error synthesizing speech:', error);
      isPlayingVoice.current = false;
      // Continue processing queue
      processVoiceQueue();
    }
  };

  const connectToServer = () => {
    const url = 'ws://localhost:8765';
    
    try {
      websocketRef.current = new WebSocket(url);
      
      websocketRef.current.onopen = () => {
        console.log('🟢 WebSocket connection to server opened');
      };
      
      websocketRef.current.onmessage = (event) => {
        try {
          const response = JSON.parse(event.data);
          console.log('📡 Server response:', response);
          
          // Handle turn messages from server (both user and assistant)
          if (response.type === 'turn' && response.data) {
            const { role, content } = response.data;
            if (content) {
              if (role === 'user') {
                // Handle streaming user messages
                setMessages(prev => {
                  const lastMessage = prev[prev.length - 1];
                  
                  // If the last message is from the user, replace its content
                  if (lastMessage && lastMessage.role === 'user') {
                    const updatedMessages = [...prev];
                    updatedMessages[updatedMessages.length - 1] = {
                      ...lastMessage,
                      content: content,
                      timestamp: new Date()
                    };
                    console.log('🔄 Updated existing user message:', content);
                    return updatedMessages;
                  } else {
                    // If the last message is from assistant or no messages, create new user message
                    const newMessage: Message = {
                      id: Date.now().toString(),
                      role: 'user',
                      content: content,
                      timestamp: new Date()
                    };
                    console.log('👤 Created new user message:', content);
                    return [...prev, newMessage];
                  }
                });
              } else if (role === 'assistant') {
                // Add assistant message to chat
                addOrUpdateAssistantMessage(content);
                console.log('🤖 Assistant message received from server:', content);
                
                // Synthesize and play speech for assistant messages
                synthesizeAndPlaySpeech(content);
              }
            }
          }
        } catch (error) {
          console.error('❌ Error parsing server response:', error);
        }
      };
      
      websocketRef.current.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };
      
      websocketRef.current.onclose = () => {
        console.log('🔴 WebSocket connection closed');
      };
      
      return true;
    } catch (error) {
      console.error('❌ Error creating WebSocket:', error);
      return false;
    }
  };

  const sendAudioToServer = (audioArray: Float32Array) => {
    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected');
      return;
    }

    try {
      // Convert Float32Array to Int16Array for server
      const int16Array = new Int16Array(audioArray.length);
      for (let i = 0; i < audioArray.length; i++) {
        int16Array[i] = Math.max(-32768, Math.min(32767, audioArray[i] * 32768));
      }
      
      // Convert to base64 for JSON transmission - use a more efficient method
      const uint8Array = new Uint8Array(int16Array.buffer);
      let binaryString = '';
      for (let i = 0; i < uint8Array.length; i++) {
        binaryString += String.fromCharCode(uint8Array[i]);
      }
      const base64Audio = btoa(binaryString);
      
      // Send audio data as structured message
      const audioMessage = {
        type: "audio",
        data: base64Audio
      };
      
      websocketRef.current.send(JSON.stringify(audioMessage));
    } catch (error) {
      console.error('❌ Error sending audio to server:', error);
    }
  };

  const sendAudioToServerWithTimestamp = (audioArray: Float32Array, startTime: number) => {
    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      console.error('❌ WebSocket not connected');
      return;
    }

    try {
      // Convert Float32Array to Int16Array for server
      const int16Array = new Int16Array(audioArray.length);
      for (let i = 0; i < audioArray.length; i++) {
        int16Array[i] = Math.max(-32768, Math.min(32767, audioArray[i] * 32768));
      }
      
      // Convert to base64 for JSON transmission - use a more efficient method
      const uint8Array = new Uint8Array(int16Array.buffer);
      let binaryString = '';
      for (let i = 0; i < uint8Array.length; i++) {
        binaryString += String.fromCharCode(uint8Array[i]);
      }
      const base64Audio = btoa(binaryString);
      
      // Send audio data as structured message with timestamp
      const audioMessage = {
        type: "audio",
        data: base64Audio,
        startTime: startTime
      };
      
      websocketRef.current.send(JSON.stringify(audioMessage));
    } catch (error) {
      console.error('❌ Error sending audio to server:', error);
    }
  };

  const createAudioClip = (audioData: Float32Array) => {
    const newClip: AudioClip = {
      id: Date.now().toString(),
      timestamp: new Date(),
      audioData: audioData,
      duration: audioData.length / 16000, // Assuming 16kHz sample rate
      isPlaying: false
    };
    
    setAudioClips(prev => [...prev, newClip]); // Add to end of list (earliest to latest)
    console.log('🎵 Audio clip created:', newClip.id, 'Duration:', newClip.duration.toFixed(2), 's');
  };

  const playAudioClip = async (clip: AudioClip) => {
    try {
      // Initialize audio context if needed
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      // Create audio buffer
      const audioBuffer = audioContextRef.current.createBuffer(1, clip.audioData.length, 16000);
      audioBuffer.getChannelData(0).set(clip.audioData);

      // Create audio source
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);

      // Update playing state
      setAudioClips(prev => prev.map(c => 
        c.id === clip.id ? { ...c, isPlaying: true } : c
      ));

      // Play audio
      source.start();
      
      // Handle playback end
      source.onended = () => {
        setAudioClips(prev => prev.map(c => 
          c.id === clip.id ? { ...c, isPlaying: false } : c
        ));
      };

      console.log('▶️ Playing audio clip:', clip.id);
    } catch (error) {
      console.error('❌ Error playing audio clip:', error);
    }
  };

  const deleteAudioClip = (clipId: string) => {
    setAudioClips(prev => prev.filter(clip => clip.id !== clipId));
    console.log('🗑️ Deleted audio clip:', clipId);
  };

  const clearAllAudioClips = () => {
    setAudioClips([]);
    console.log('🗑️ Cleared all audio clips');
  };

  const toggleVAD = async () => {
    if (!isStarted) {
      await startVAD();
    } else {
      stopVAD();
    }
  };

  const startVAD = async () => {
    console.log('🚀 Starting VAD...');
    setIsStarting(true);
    
    try {
      // Connect to server WebSocket
      if (!connectToServer()) {
        throw new Error('Failed to connect to server');
      }
      
      // Wait for VAD library to be available
      if (!window.vad) {
        throw new Error('VAD library not loaded yet');
      }
      
      console.log('📦 Initializing VAD...');
      vadInstanceRef.current = await window.vad.MicVAD.new({
        model: "v5",
        positiveSpeechThreshold: 0.6,
        negativeSpeechThreshold: 0.4,
        minSpeechFrames: 5,
        preSpeechPadFrames: 5,
        onFrameProcessed: (probs: any, frame: Float32Array) => {
          if (probs.isSpeech > 0.7) {
            setHasVoiceActivity(true);
            if (speechStartTimeRef.current === null) {
              speechStartTimeRef.current = Date.now();
              console.log('🎤 Speech started at:', new Date(speechStartTimeRef.current).toISOString());
            }
            sendAudioToServer(frame);
          }
        },
        onSpeechEnd: (audioArray: Float32Array) => {
          if (isProcessingSpeechEnd.current) {
            console.log('🔄 Speech end already being processed, skipping...');
            return;
          }
          
          isProcessingSpeechEnd.current = true;
          
          try {
            console.log('🔇 Speech ended, processing final audio...');
            setHasVoiceActivity(false);
            
            // Create audio clip from the complete speech segment
            createAudioClip(audioArray);
            
            // Send final audio chunk to server with speech start timestamp
            sendAudioToServerWithTimestamp(audioArray, speechStartTimeRef.current || Date.now());
            
            // Reset speech start time
            speechStartTimeRef.current = null;
            
          } catch (error) {
            console.error('❌ Error in onSpeechEnd:', error);
          } finally {
            // Reset the flag after a short delay to allow for any cleanup
            setTimeout(() => {
              isProcessingSpeechEnd.current = false;
            }, 100);
          }
        },
      });
      
      console.log('✅ VAD initialized successfully');
      
      // Start VAD
      console.log('🎙️ Starting VAD...');
      vadInstanceRef.current.start();
      console.log('🎙️ VAD started');
      setIsStarted(true);
      setIsStarting(false);
      console.log('✅ VAD state set to started');
      
    } catch (error) {
      console.error('❌ Error starting VAD:', error);
      alert('Error starting voice activity detection. Please check permissions.');
      setIsStarting(false);
    }
  };

  const stopVAD = () => {
    if (vadInstanceRef.current) {
      vadInstanceRef.current.pause();
    }
  
    // Kill all synthesis and clear voice queue
    voiceQueue.current = [];
    isPlayingVoice.current = false;
    console.log("🔇 Voice synthesis stopped and queue cleared");
  
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
      console.log("🔌 WebSocket connection closed and reset");
    }
  
    setIsStarted(false);
    setHasVoiceActivity(false);
    console.log("🛑 VAD stopped");
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (vadInstanceRef.current) {
        vadInstanceRef.current.pause();
      }
      if (websocketRef.current) {
        websocketRef.current.close();
      }
      // Kill all synthesis and clear voice queue on unmount
      voiceQueue.current = [];
      isPlayingVoice.current = false;
      console.log("🧹 Component unmounted - synthesis stopped and queue cleared");
    };
  }, []);

  const getButtonColor = () => {
    if (isStarting) return 'bg-yellow-500 hover:bg-yellow-600';
    if (isStarted && hasVoiceActivity) return 'bg-green-500 hover:bg-green-600';
    if (isStarted) return 'bg-red-500 hover:bg-red-600';
    return 'bg-blue-500 hover:bg-blue-600';
  };

  const getButtonText = () => {
    if (isStarting) return 'Starting...';
    if (isStarted) return 'Stop';
    return 'Start';
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">Voice Chat</h1>
        <p className="text-gray-600 text-sm">Speak to start a conversation</p>
      </div>

      <div className="flex-1 flex">
        {/* Chat Messages */}
        <div className="flex-1 flex flex-col">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <div className="text-6xl mb-4">🎤</div>
                <p className="text-lg">No messages yet</p>
                <p className="text-sm">Click "Start" and speak to begin the conversation</p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 text-gray-800'
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    <p className={`text-xs mt-1 ${
                      message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {formatTime(message.timestamp)}
                    </p>
                  </div>
                </div>
              ))
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Control Panel */}
          <div className="bg-white border-t p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={toggleVAD}
                  disabled={isStarting}
                  className={`px-6 py-3 rounded-lg text-white font-semibold transition-colors ${getButtonColor()} disabled:opacity-50`}
                >
                  {getButtonText()}
                </button>
                
                {hasVoiceActivity && (
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse mr-2"></div>
                    <span className="text-sm text-gray-600">Voice detected</span>
                  </div>
                )}
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowAudioPanel(!showAudioPanel)}
                  className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  {showAudioPanel ? 'Hide' : 'Show'} Audio ({audioClips.length})
                </button>
                
                {audioClips.length > 0 && (
                  <button
                    onClick={clearAllAudioClips}
                    className="px-3 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Clear All
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Audio Panel */}
        {showAudioPanel && (
          <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800">Audio Recordings</h3>
              <p className="text-sm text-gray-600">Track audio sent to server</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {audioClips.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-4xl mb-2">🎵</div>
                  <p className="text-sm">No audio recordings yet</p>
                  <p className="text-xs">Start speaking to record audio</p>
                </div>
              ) : (
                audioClips.map((clip) => (
                  <div key={clip.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => playAudioClip(clip)}
                          disabled={clip.isPlaying}
                          className={`p-2 rounded-full transition-colors ${
                            clip.isPlaying 
                              ? 'bg-green-500 text-white' 
                              : 'bg-blue-500 hover:bg-blue-600 text-white'
                          }`}
                        >
                          {clip.isPlaying ? '⏸️' : '▶️'}
                        </button>
                        <span className="text-sm font-medium text-gray-700">
                          {clip.duration.toFixed(1)}s
                        </span>
                      </div>
                      
                      <button
                        onClick={() => deleteAudioClip(clip.id)}
                        className="p-1 text-red-500 hover:text-red-700 transition-colors"
                      >
                        🗑️
                      </button>
                    </div>
                    
                    <div className="text-xs text-gray-500">
                      {formatTime(clip.timestamp)}
                    </div>
                    
                    {clip.isPlaying && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-1">
                          <div className="bg-green-500 h-1 rounded-full animate-pulse"></div>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

