#!/usr/bin/env python3
"""
Nova Sonic Style Generator for EssenceMirror
Bidirectional audio conversation system for style recommendations
"""

import os
import asyncio
import base64
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Nova Sonic dependencies
try:
    from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
    from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
    from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
    from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver
    NOVA_SONIC_AVAILABLE = True
except ImportError as e:
    logger.error(f"Nova Sonic dependencies not available: {str(e)}")
    NOVA_SONIC_AVAILABLE = False

class NovaSonicStyleGenerator:
    """Nova Sonic generator for EssenceMirror style conversations"""
    
    def __init__(self, model_id='amazon.nova-sonic-v1:0', region='us-east-1'):
        self.model_id = model_id
        self.region = region
        self.client = None
        self.stream = None
        self.is_active = False
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        self.response_queue = asyncio.Queue()
        self.audio_queue = asyncio.Queue()
        
        # Voice configuration
        self.voice_options = {
            "Joanna": "Professional Female (US)",
            "Matthew": "Warm Male (US)",
            "Amy": "Elegant Female (British)",
            "Brian": "Authoritative Male (British)"
        }
        self.default_voice = "Joanna"
        
    def _initialize_client(self):
        """Initialize the Nova Sonic client"""
        try:
            # Ensure environment variables are set
            if not os.environ.get('AWS_ACCESS_KEY_ID') or not os.environ.get('AWS_SECRET_ACCESS_KEY'):
                logger.error("AWS credentials not found in environment variables")
                return False
            
            config = Config(
                endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
                region=self.region,
                aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
                http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
                http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
            )
            self.client = BedrockRuntimeClient(config=config)
            logger.info("Nova Sonic client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Nova Sonic client: {str(e)}")
            return False
    
    async def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Send an event to the bidirectional stream"""
        try:
            event_json = json.dumps(event_data)
            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
            )
            await self.stream.input_stream.send(event)
            return True
        except Exception as e:
            logger.error(f"Failed to send event: {str(e)}")
            return False
    
    async def start_style_session(self, voice_id: Optional[str] = None) -> bool:
        """Start a Nova Sonic session for style conversations"""
        try:
            if not NOVA_SONIC_AVAILABLE:
                logger.error("Nova Sonic dependencies not available")
                return False
            
            if not self.client:
                if not self._initialize_client():
                    return False
            
            # Initialize bidirectional stream
            self.stream = await self.client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            )
            self.is_active = True
            logger.info("Nova Sonic bidirectional stream established")
            
            # Use provided voice or default
            selected_voice = voice_id if voice_id in self.voice_options else self.default_voice
            
            # Send session start
            await self.send_event({
                "event": {
                    "sessionStart": {
                        "inferenceConfiguration": {
                            "maxTokens": 1024,
                            "topP": 0.9,
                            "temperature": 0.7
                        }
                    }
                }
            })
            
            # Send prompt start with audio configuration
            await self.send_event({
                "event": {
                    "promptStart": {
                        "promptName": self.prompt_name,
                        "textOutputConfiguration": {
                            "mediaType": "text/plain"
                        },
                        "audioOutputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": 24000,
                            "sampleSizeBits": 16,
                            "channelCount": 1,
                            "voiceId": selected_voice,
                            "encoding": "base64",
                            "audioType": "SPEECH"
                        }
                    }
                }
            })
            
            # Send style-focused system prompt
            await self._send_style_system_prompt()
            
            # Start response processing
            asyncio.create_task(self._process_responses())
            
            logger.info(f"Style session started with voice: {selected_voice}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start style session: {str(e)}")
            return False
    
    async def _send_style_system_prompt(self):
        """Send system prompt optimized for style conversations"""
        try:
            # Start system content
            await self.send_event({
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name,
                        "type": "TEXT",
                        "interactive": True,
                        "role": "SYSTEM",
                        "textInputConfiguration": {
                            "mediaType": "text/plain"
                        }
                    }
                }
            })
            
            # Style consultant system prompt
            system_prompt = """You are EssenceMirror's AI style consultant - a professional, encouraging, and knowledgeable fashion advisor. 

Your expertise includes:
- Personal style analysis and recommendations
- Color theory and seasonal palettes
- Body type and fit guidance
- Occasion-appropriate styling
- Confidence building through fashion

Your conversation style:
- Warm, supportive, and professional
- Ask clarifying questions about preferences, lifestyle, and occasions
- Provide specific, actionable recommendations
- Keep responses conversational and encouraging
- Focus on building the user's confidence and personal style

Remember: Every person has their own unique style - help them discover and embrace it!"""
            
            # Send system prompt
            await self.send_event({
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name,
                        "content": system_prompt
                    }
                }
            })
            
            # End system content
            await self.send_event({
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": self.content_name
                    }
                }
            })
            
            logger.info("Style system prompt configured")
            
        except Exception as e:
            logger.error(f"Failed to send system prompt: {str(e)}")
    
    async def send_text_message(self, message: str) -> bool:
        """Send a text message to Nova Sonic"""
        try:
            content_name = f"user_text_{uuid.uuid4()}"
            
            # Start user content
            await self.send_event({
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "type": "TEXT",
                        "interactive": True,
                        "role": "USER",
                        "textInputConfiguration": {
                            "mediaType": "text/plain"
                        }
                    }
                }
            })
            
            # Send message
            await self.send_event({
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "content": message
                    }
                }
            })
            
            # End user content
            await self.send_event({
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": content_name
                    }
                }
            })
            
            logger.info(f"Text message sent: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send text message: {str(e)}")
            return False
    
    async def send_audio_chunk(self, audio_bytes: bytes) -> bool:
        """Send audio chunk to Nova Sonic"""
        try:
            if not self.is_active:
                return False
            
            # Start audio content if not already started
            if not hasattr(self, '_audio_started'):
                await self.send_event({
                    "event": {
                        "contentStart": {
                            "promptName": self.prompt_name,
                            "contentName": self.audio_content_name,
                            "type": "AUDIO",
                            "interactive": True,
                            "role": "USER",
                            "audioInputConfiguration": {
                                "mediaType": "audio/lpcm",
                                "sampleRateHertz": 16000,
                                "sampleSizeBits": 16,
                                "channelCount": 1,
                                "audioType": "SPEECH",
                                "encoding": "base64"
                            }
                        }
                    }
                })
                self._audio_started = True
            
            # Send audio chunk
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            await self.send_event({
                "event": {
                    "audioInput": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name,
                        "content": audio_base64
                    }
                }
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {str(e)}")
            return False
    
    async def end_audio_input(self) -> bool:
        """End audio input stream"""
        try:
            if hasattr(self, '_audio_started'):
                await self.send_event({
                    "event": {
                        "contentEnd": {
                            "promptName": self.prompt_name,
                            "contentName": self.audio_content_name
                        }
                    }
                })
                delattr(self, '_audio_started')
                logger.info("Audio input ended")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end audio input: {str(e)}")
            return False
    
    async def _process_responses(self):
        """Process responses from Nova Sonic"""
        try:
            logger.info("Starting Nova Sonic response processing...")
            
            while self.is_active:
                output = await self.stream.await_output()
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode('utf-8')
                    json_data = json.loads(response_data)
                    
                    if 'event' in json_data:
                        # Handle text output
                        if 'textOutput' in json_data['event']:
                            text = json_data['event']['textOutput']['content']
                            await self.response_queue.put({
                                'type': 'text',
                                'content': text,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                        
                        # Handle audio output
                        elif 'audioOutput' in json_data['event']:
                            audio_content = json_data['event']['audioOutput']['content']
                            audio_bytes = base64.b64decode(audio_content)
                            await self.audio_queue.put({
                                'type': 'audio',
                                'content': audio_bytes,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                        
                        # Handle content events
                        elif 'contentStart' in json_data['event']:
                            role = json_data['event']['contentStart'].get('role', 'Unknown')
                            logger.info(f"Content started - Role: {role}")
                        
                        elif 'contentEnd' in json_data['event']:
                            logger.info("Content ended")
                            
        except Exception as e:
            logger.error(f"Error processing responses: {str(e)}")
    
    async def get_response(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Get the next response from Nova Sonic"""
        try:
            response = await asyncio.wait_for(self.response_queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            return None
    
    async def get_audio_response(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Get the next audio response from Nova Sonic"""
        try:
            audio_response = await asyncio.wait_for(self.audio_queue.get(), timeout=timeout)
            return audio_response
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting audio response: {str(e)}")
            return None
    
    async def end_session(self):
        """End the Nova Sonic session"""
        try:
            if not self.is_active:
                return
            
            self.is_active = False
            
            # End any ongoing audio input
            await self.end_audio_input()
            
            # Send prompt end
            await self.send_event({
                "event": {
                    "promptEnd": {
                        "promptName": self.prompt_name
                    }
                }
            })
            
            # Send session end
            await self.send_event({
                "event": {
                    "sessionEnd": {}
                }
            })
            
            # Close stream
            await self.stream.input_stream.close()
            
            logger.info("Nova Sonic session ended successfully")
            
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
    
    def get_available_voices(self) -> Dict[str, str]:
        """Get available voice options"""
        return self.voice_options

# Test function
async def test_nova_sonic_style_generator():
    """Test the Nova Sonic Style Generator"""
    try:
        print("🎵 Testing Nova Sonic Style Generator")
        print("=" * 60)
        
        # Create generator
        generator = NovaSonicStyleGenerator()
        
        # Start session
        if not await generator.start_style_session():
            print("❌ Failed to start session")
            return False
        
        # Test conversation
        style_questions = [
            "Hi! I need help finding my personal style",
            "I work in a corporate environment but want to express my personality",
            "What colors would work best for someone with my skin tone?",
            "Can you recommend some versatile pieces for my wardrobe?"
        ]
        
        for question in style_questions:
            print(f"\n👤 User: {question}")
            await generator.send_text_message(question)
            
            # Get response
            response = await generator.get_response(timeout=15.0)
            if response:
                print(f"🎙️ EssenceMirror: {response['content']}")
            
            # Check for audio response
            audio_response = await generator.get_audio_response(timeout=5.0)
            if audio_response:
                # Save audio for testing
                timestamp = datetime.now().strftime('%H%M%S')
                audio_file = f"style_response_{timestamp}.wav"
                with open(audio_file, 'wb') as f:
                    f.write(audio_response['content'])
                print(f"🎵 Audio saved: {audio_file}")
        
        # End session
        await generator.end_session()
        
        print("\n✅ Nova Sonic Style Generator test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Ensure AWS credentials are set
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        print("⚠️ Setting AWS credentials from profile...")
        os.system("export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)")
        os.system("export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)")
        os.system("export AWS_DEFAULT_REGION=$(aws configure get region)")
    
    asyncio.run(test_nova_sonic_style_generator())
