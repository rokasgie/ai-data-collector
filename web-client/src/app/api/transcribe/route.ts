import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@deepgram/sdk';

export async function POST(request: NextRequest) {
  try {
    const { audioData, mimeType } = await request.json();
    
    // Get DeepGram API key from server environment
    const deepgramApiKey = process.env.DEEPGRAM_API_KEY;
    
    if (!deepgramApiKey) {
      return NextResponse.json(
        { error: 'DeepGram API key not configured' },
        { status: 500 }
      );
    }
    
    // Create DeepGram client
    const deepgram = createClient(deepgramApiKey);
    
    // Convert base64 to buffer
    const buffer = Buffer.from(audioData, 'base64');
    
    // Transcribe using DeepGram SDK
    const { result, error } = await deepgram.listen.prerecorded.transcribeFile(
      buffer,
      {
        model: 'nova-3',
        smart_format: true,
        mimetype: mimeType,
      }
    );
    
    if (error) {
      console.error('DeepGram error:', error);
      return NextResponse.json(
        { error: 'DeepGram transcription failed', details: error.message },
        { status: 500 }
      );
    }
    
    // Extract transcript from DeepGram response
    const transcript = result?.results?.channels?.[0]?.alternatives?.[0]?.transcript || 'No transcript found';
    
    console.log('✅ Transcription successful:', transcript);
    
    return NextResponse.json({ transcript, fullResponse: result });
    
  } catch (error) {
    console.error('Transcription error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
} 