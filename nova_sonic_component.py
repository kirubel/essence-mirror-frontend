"""
Nova Sonic Bidirectional Audio Component for EssenceMirror
Real-time voice conversations with AI style consultant
"""

import streamlit as st
import asyncio
import os
import sys
import json
import time
import uuid
import tempfile
from datetime import datetime
import logging
import threading
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import Nova Sonic dependencies
try:
    # Add infrastructure path for local development
    sys.path.append('/Users/kirubelaklilu/Documents/EssenceMirror/essence-mirror-infrastructure')
    from nova_sonic_style_generator import NovaSonicStyleGenerator, NOVA_SONIC_AVAILABLE
    NOVA_SONIC_COMPONENT_AVAILABLE = True
except ImportError as e:
    st.error(f"Error importing Nova Sonic generator: {str(e)}")
    st.info("Nova Sonic bidirectional audio features may not be available.")
    NOVA_SONIC_COMPONENT_AVAILABLE = False
    NovaSonicStyleGenerator = None

# Voice options for Nova Sonic
VOICE_OPTIONS = {
    "Joanna": "👩 Joanna - Professional Female (US)",
    "Matthew": "👨 Matthew - Warm Male (US)", 
    "Amy": "👩 Amy - Elegant Female (British)",
    "Brian": "👨 Brian - Authoritative Male (British)"
}

def render_nova_sonic_tab(session_id, analysis_complete, style_analysis_data=None):
    """Render the Nova Sonic bidirectional audio tab"""
    
    st.markdown("### 🎙️ Voice Style Consultant")
    st.markdown("**BREAKTHROUGH**: Have a real-time voice conversation with your AI style consultant!")
    
    # Check if Nova Sonic is available
    if not NOVA_SONIC_COMPONENT_AVAILABLE:
        st.error("🚧 Nova Sonic bidirectional audio is currently unavailable")
        st.info("""
        **Missing Component**: The Nova Sonic generator is not available.
        
        **This could be because:**
        - The Nova Sonic infrastructure component is not deployed
        - Import path issues in the deployment environment
        - Missing Nova Sonic dependencies
        - AWS credentials not configured for Nova Sonic
        
        **For now, you can:**
        - Use the Style Analysis and Visual features
        - Check back later when the component is available
        """)
        return
    
    # Success message
    st.success("🎉 **BREAKTHROUGH**: Real-time bidirectional voice conversations with AI!")
    
    # Feature highlights
    st.markdown("""
    #### 🌟 Revolutionary Features:
    - 🎙️ **Speak naturally** - Just talk to your style consultant
    - 🎧 **Hear responses** - AI responds with professional voice
    - 💬 **Real-time conversation** - Natural back-and-forth dialogue
    - 🎯 **Style-focused** - Specialized in fashion and style advice
    - 🎵 **Multiple voices** - Choose your preferred AI consultant
    """)
    
    # Voice selection
    st.markdown("#### 🎙️ Choose Your AI Style Consultant")
    selected_voice = st.selectbox(
        "Select your preferred voice:",
        options=list(VOICE_OPTIONS.keys()),
        format_func=lambda x: VOICE_OPTIONS[x],
        index=0,  # Default to Joanna
        help="Choose the voice for your AI style consultant"
    )
    
    # Show voice description
    st.info(f"Selected: {VOICE_OPTIONS[selected_voice]}")
    
    # Conversation interface
    st.markdown("#### 🎤 Voice Conversation")
    
    # Initialize session state for Nova Sonic
    if 'nova_sonic_session' not in st.session_state:
        st.session_state.nova_sonic_session = None
    if 'nova_sonic_active' not in st.session_state:
        st.session_state.nova_sonic_active = False
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # Session controls
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🎙️ Start Voice Session", type="primary", disabled=st.session_state.nova_sonic_active):
            start_nova_sonic_session(selected_voice, session_id)
    
    with col2:
        if st.button("⏹️ End Session", disabled=not st.session_state.nova_sonic_active):
            end_nova_sonic_session()
    
    with col3:
        if st.button("🔄 Reset Conversation"):
            st.session_state.conversation_history = []
            st.rerun()
    
    # Session status
    if st.session_state.nova_sonic_active:
        st.success("🟢 Voice session active - You can now speak!")
    else:
        st.info("🔴 Voice session inactive - Click 'Start Voice Session' to begin")
    
    # Text input for testing (fallback)
    st.markdown("#### 💬 Text Input (Testing Mode)")
    st.info("Use text input to test the conversation while we work on microphone integration")
    
    text_input = st.text_input(
        "Type your style question:",
        placeholder="e.g., 'I need help choosing an outfit for a job interview'",
        disabled=not st.session_state.nova_sonic_active
    )
    
    if st.button("📤 Send Text Message", disabled=not st.session_state.nova_sonic_active or not text_input):
        send_text_to_nova_sonic(text_input)
    
    # Conversation history
    if st.session_state.conversation_history:
        st.markdown("#### 💭 Conversation History")
        
        for i, message in enumerate(st.session_state.conversation_history):
            if message['role'] == 'user':
                st.markdown(f"**👤 You:** {message['content']}")
            else:
                st.markdown(f"**🎙️ Style Consultant:** {message['content']}")
                
                # Show audio player if available
                if 'audio_file' in message:
                    try:
                        with open(message['audio_file'], 'rb') as audio_file:
                            audio_bytes = audio_file.read()
                            st.audio(audio_bytes, format='audio/wav')
                    except Exception as e:
                        st.error(f"Error playing audio: {str(e)}")
            
            st.markdown("---")
    
    # Instructions and tips
    st.markdown("#### 💡 How to Use Voice Conversations")
    st.info("""
    **🎯 Getting Started:**
    1. Choose your preferred AI voice consultant
    2. Click "Start Voice Session" 
    3. Use text input to test conversations (microphone coming soon!)
    4. Have natural conversations about style and fashion
    
    **💬 Conversation Ideas:**
    - "I need help finding my personal style"
    - "What should I wear to a job interview?"
    - "Help me choose colors that suit me"
    - "I want to update my wardrobe for the new season"
    - "What are some versatile pieces I should own?"
    
    **🎵 Features:**
    - Real-time AI responses with professional voice
    - Style-focused conversations and recommendations
    - Personalized advice based on your preferences
    - Natural, encouraging conversation style
    """)

def start_nova_sonic_session(voice_id: str, session_id: str):
    """Start a Nova Sonic voice session"""
    try:
        with st.spinner("🎙️ Starting voice session with AI style consultant..."):
            # Set AWS credentials for Nova Sonic
            setup_aws_credentials()
            
            # Create Nova Sonic generator
            generator = NovaSonicStyleGenerator()
            
            # Start session in a separate thread (since Streamlit doesn't support async directly)
            def start_session():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(generator.start_style_session(voice_id))
                loop.close()
                return success, generator
            
            # Run in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(start_session)
                success, generator = future.result(timeout=30)
            
            if success:
                st.session_state.nova_sonic_session = generator
                st.session_state.nova_sonic_active = True
                st.success(f"✅ Voice session started with {voice_id}!")
                st.rerun()
            else:
                st.error("❌ Failed to start voice session")
                
    except Exception as e:
        st.error(f"❌ Error starting voice session: {str(e)}")
        logger.error(f"Nova Sonic session start error: {str(e)}")

def end_nova_sonic_session():
    """End the Nova Sonic voice session"""
    try:
        if st.session_state.nova_sonic_session:
            with st.spinner("⏹️ Ending voice session..."):
                # End session in thread
                def end_session():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(st.session_state.nova_sonic_session.end_session())
                    loop.close()
                
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(end_session)
                    future.result(timeout=10)
                
                st.session_state.nova_sonic_session = None
                st.session_state.nova_sonic_active = False
                st.success("✅ Voice session ended")
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Error ending voice session: {str(e)}")
        logger.error(f"Nova Sonic session end error: {str(e)}")

def send_text_to_nova_sonic(message: str):
    """Send text message to Nova Sonic and get response"""
    try:
        if not st.session_state.nova_sonic_session or not st.session_state.nova_sonic_active:
            st.error("❌ No active voice session")
            return
        
        with st.spinner("🎙️ AI Style Consultant is thinking..."):
            # Add user message to history
            st.session_state.conversation_history.append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Send message and get response in thread
            def send_and_receive():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Send message
                success = loop.run_until_complete(
                    st.session_state.nova_sonic_session.send_text_message(message)
                )
                
                if success:
                    # Get text response
                    text_response = loop.run_until_complete(
                        st.session_state.nova_sonic_session.get_response(timeout=15.0)
                    )
                    
                    # Get audio response
                    audio_response = loop.run_until_complete(
                        st.session_state.nova_sonic_session.get_audio_response(timeout=10.0)
                    )
                    
                    loop.close()
                    return text_response, audio_response
                else:
                    loop.close()
                    return None, None
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(send_and_receive)
                text_response, audio_response = future.result(timeout=30)
            
            # Process responses
            if text_response:
                response_data = {
                    'role': 'assistant',
                    'content': text_response['content'],
                    'timestamp': text_response['timestamp']
                }
                
                # Save audio if available
                if audio_response:
                    timestamp = datetime.now().strftime('%H%M%S')
                    audio_file = f"nova_sonic_response_{timestamp}.wav"
                    
                    with open(audio_file, 'wb') as f:
                        f.write(audio_response['content'])
                    
                    response_data['audio_file'] = audio_file
                
                st.session_state.conversation_history.append(response_data)
                st.success("✅ Response received!")
                st.rerun()
            else:
                st.error("❌ No response received from AI consultant")
                
    except Exception as e:
        st.error(f"❌ Error in conversation: {str(e)}")
        logger.error(f"Nova Sonic conversation error: {str(e)}")

def setup_aws_credentials():
    """Setup AWS credentials for Nova Sonic"""
    try:
        # Check if credentials are already set
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
            return True
        
        # Try to get from AWS CLI configuration
        import subprocess
        try:
            access_key = subprocess.check_output(['aws', 'configure', 'get', 'aws_access_key_id']).decode().strip()
            secret_key = subprocess.check_output(['aws', 'configure', 'get', 'aws_secret_access_key']).decode().strip()
            region = subprocess.check_output(['aws', 'configure', 'get', 'region']).decode().strip()
            
            os.environ['AWS_ACCESS_KEY_ID'] = access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = secret_key
            os.environ['AWS_DEFAULT_REGION'] = region
            
            logger.info("AWS credentials set from CLI configuration")
            return True
            
        except subprocess.CalledProcessError:
            logger.error("Failed to get AWS credentials from CLI")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up AWS credentials: {str(e)}")
        return False

def test_nova_sonic_component():
    """Test function for the Nova Sonic component"""
    st.markdown("### 🧪 Nova Sonic Component Test")
    
    if NOVA_SONIC_COMPONENT_AVAILABLE:
        st.success("✅ Nova Sonic component is available")
        
        # Test AWS credentials
        if setup_aws_credentials():
            st.success("✅ AWS credentials configured")
        else:
            st.error("❌ AWS credentials not available")
        
        # Show available voices
        st.markdown("**Available Voices:**")
        for voice_id, description in VOICE_OPTIONS.items():
            st.info(f"• {description}")
        
    else:
        st.error("❌ Nova Sonic component not available")
        st.info("Check dependencies and infrastructure setup")

# Main function for standalone testing
def main():
    """Main function for testing the component"""
    st.set_page_config(
        page_title="EssenceMirror Nova Sonic Test",
        page_icon="🎙️",
        layout="wide"
    )
    
    st.title("🎙️ EssenceMirror Nova Sonic Component Test")
    
    # Test the component
    test_nova_sonic_component()
    
    # Full component test
    st.markdown("---")
    render_nova_sonic_tab(
        session_id="test_session_123",
        analysis_complete=True,
        style_analysis_data=None
    )

if __name__ == "__main__":
    main()
