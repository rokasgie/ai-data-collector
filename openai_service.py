import asyncio
import websockets
import json
import logging
import os
import openai
from dotenv import load_dotenv
import nltk
from typing import Callable, Awaitable
nltk.download('punkt_tab')
from nltk.tokenize import sent_tokenize

from call_info import CallState, PatientInfo, CALL_STATE_EXPLANATIONS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OpenAIService")

class OpenAIService:
    def __init__(self):
        self.openai_client = None
        self.conversation_history = []
        self.call_state = CallState()
        self.patient_info = PatientInfo()
        
        self.name = "Spike Bot"

        self.system_message = f"""
            You are {self.name}, a data collector working for Spike Clinical. 
            Your role is to gather necessary data from the insurance company representatives.
            You call them to get the information about the patien's insurance.

            The information about the patient that you can use to identify the patient:
            {json.dumps(self.patient_info.model_dump(), indent=2)}

            You don't offer assistance to the representative. You only ask for the information and respond to their questions to identify the patient.
        """
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("Missing OPENAI_API_KEY in environment")
            raise ValueError("OPENAI_API_KEY is required")
        
        self.openai_client = openai.AsyncOpenAI(api_key=api_key)
        logger.info("🤖 OpenAI client initialized")
        
    def get_call_state_explanation_message(self):
        system_message = self.system_message + "\nYou should summarize the conversation in a single paragraphusing the following information:\n"
        call_state_dict = self.call_state.model_dump()
        call_state_info = [f"{key} {value}" for key, value in call_state_dict.items()]
        return system_message + "\n\n".join(call_state_info)
    
    def get_missing_information_message(self):
        call_state_dict = self.call_state.model_dump()
        missing_information = [f"{key} - {CALL_STATE_EXPLANATIONS[key]}" for key, value in call_state_dict.items() if value is None]
        return f" {self.system_message}\nYou should ask the representative for the following information:\n{missing_information[0]}"
        
    def get_system_message(self):
        if len(self.conversation_history) == 1:
            return {
                "role": "system",
                "content": self.system_message
            }
        else:
            if all(value is not None for value in self.call_state.model_dump().values()):
                return {
                    "role": "system",
                    "content": self.get_call_state_explanation_message()
                }
            else:
                return {
                    "role": "system",
                    "content": self.get_missing_information_message()
                }
            return {
                "role": "system",
                "content": self.system_message
            }
        
    def build_messages(self):
        messages = self.conversation_history[-30:]
        system_message = self.get_system_message()
        return [system_message] + messages
    
    async def parse_response(self, response_messages):
        """Parse the conversation messages into call_state via OpenAI parsing endpoint."""
        try:
            system_message = {
                "role": "system",
                "content": """
                    Parse the following conversation into a CallState object.
                    - Only extract values explicitly stated in the conversation.
                    - If a value is not mentioned, set it to `None`.
                    - Do not infer, assume, or guess values based on typical defaults.
                """
            }
            messages = [system_message] + response_messages
            logger.info(f"📤 Sending to OpenAI for parsing: {messages}")
            response = await self.openai_client.responses.parse(
                model="gpt-4o-mini",
                input=messages,
                text_format=CallState
            )
            
            parsed_state = response.output_parsed
            if parsed_state is not None:
                # Update existing call_state dict
                for key, value in parsed_state.model_dump().items():
                    if value is not None:
                        setattr(self.call_state, key, value)

            logger.info(f"📊 Updated call state via parsing endpoint: {self.call_state}")

        except Exception as e:
            logger.error(f"❌ Error parsing response: {e}")

    async def send_to_openai(self, transcript: str, response_callback: Callable[[str], Awaitable[None]]):
        """Send transcript to OpenAI and get response, sending it sentence by sentence"""
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": transcript
            })
            logger.info(f"Transcript: {transcript}")

            await self.parse_response(self.conversation_history)

            messages = self.build_messages()

            logger.info(f"📤 Sending to OpenAI: {messages[0]}")
            
            # Stream response from OpenAI
            stream = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                max_tokens=150,
                temperature=0.0
            )

            # Process response sentence by sentence
            full_response = ""
            sentence_buffer = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    sentence_buffer += content
                    full_response += content
                    
                    # Use NLTK's sent_tokenize to properly split sentences
                    sentences = sent_tokenize(sentence_buffer)
                    
                    # If we have complete sentences, send them
                    if len(sentences) > 1:
                        # Send all complete sentences except the last one (which might be incomplete)
                        for sentence in sentences[:-1]:
                            await response_callback(sentence.strip())
                        
                        # Keep the last sentence in the buffer (might be incomplete)
                        sentence_buffer = sentences[-1]
            
            if sentence_buffer.strip():
                await response_callback(sentence_buffer.strip())
            
            # Add assistant response to conversation history
            if full_response:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": full_response
                })
            
        except Exception as e:
            logger.error(f"❌ Error communicating with OpenAI: {e}")
            return None
