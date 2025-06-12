"""
Audio Style Component for EssenceMirror Streamlit App
Controlled integration of Amazon Polly text-to-speech functionality
"""

import streamlit as st
import os
import sys
import json
import time
import uuid
import tempfile
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import the audio generator
try:
    # Add infrastructure path for local development
    sys.path.append('/Users/kirubelaklilu/Documents/EssenceMirror/essence-mirror-infrastructure')
    from polly_audio_generator import EssenceMirrorAudioGenerator
    AUDIO_GENERATOR_AVAILABLE = True
except ImportError as e:
    st.error(f"Error importing audio generator: {str(e)}")
    st.info("Audio generation features may not be available.")
    AUDIO_GENERATOR_AVAILABLE = False
    EssenceMirrorAudioGenerator = None

# Configuration
SUPPORTED_VOICES = {
    "joanna": "Joanna - Professional Female (US)",
    "matthew": "Matthew - Warm Male (US)", 
    "amy": "Amy - Elegant Female (British)",
    "brian": "Brian - Authoritative Male (British)",
    "emma": "Emma - Clear Female (British)",
    "olivia": "Olivia - Friendly Female (Australian)"
}

def render_audio_style_tab(session_id, analysis_complete, style_analysis_data=None):
    """Render the Audio Style tab content"""
    
    st.markdown("### 🎵 Listen to Your Style")
    st.markdown("**NEW**: Hear your personalized style analysis with professional AI narration!")
    
    # Check if the generator is available
    if not AUDIO_GENERATOR_AVAILABLE:
        st.error("🚧 Audio generation functionality is currently unavailable")
        st.info("""
        **Missing Component**: The audio generator is not available.
        
        **This could be because:**
        - The audio generation component is not deployed
        - Import path issues in the deployment environment
        - Missing dependencies
        
        **For now, you can:**
        - Use the Style Analysis and Visual features
        - Check back later when the component is available
        """)
        return
    
    # Success message
    st.success("🎉 **NEW**: Professional AI narration of your style analysis!")
    
    # Voice selection
    st.markdown("#### 🎙️ Choose Your Narrator")
    selected_voice = st.selectbox(
        "Select voice for narration:",
        options=list(SUPPORTED_VOICES.keys()),
        format_func=lambda x: SUPPORTED_VOICES[x],
        index=0,  # Default to Joanna
        help="Choose the voice that you'd like to narrate your style analysis"
    )
    
    # Show voice description
    st.info(f"Selected: {SUPPORTED_VOICES[selected_voice]}")
    
    # Check if analysis is complete
    if not analysis_complete:
        st.warning("⏳ Complete your style analysis first to generate audio content!")
        st.info("Upload a photo and get your style analysis in the 'Style Analysis' tab, then return here for audio narration.")
        return
    
    # Audio generation section
    st.markdown("#### 🎵 Generate Audio Content")
    
    # Sample data for testing if no real analysis available
    if not style_analysis_data:
        st.info("Using sample style analysis for demonstration")
        style_analysis_data = {
            "analysis": {
                "personality": "sophisticated and elegant",
                "aesthetic": "modern minimalism with classic touches",
                "dominant_colors": ["navy blue", "warm gray", "cream"]
            },
            "recommendations": [
                "tailored blazer in navy",
                "elegant midi dress", 
                "classic white button-down",
                "comfortable flats in neutral tones"
            ],
            "colors": ["navy blue", "warm gray", "cream", "soft white"]
        }
    
    # Generate audio button
    if st.button("🎵 Generate Audio Narration", type="primary"):
        generate_audio_content(style_analysis_data, selected_voice, session_id)

def generate_audio_content(style_analysis_data, voice_preference, session_id):
    """Generate audio content for style analysis"""
    
    if not AUDIO_GENERATOR_AVAILABLE:
        st.error("Audio generator not available")
        return
    
    try:
        with st.spinner("🎵 Generating your personalized audio content..."):
            # Initialize the audio generator
            generator = EssenceMirrorAudioGenerator(profile_name=None)  # Use environment credentials
            
            # Generate audio for all sections
            audio_results = generator.generate_style_analysis_audio(
                style_analysis=style_analysis_data,
                voice_preference=voice_preference
            )
            
            st.success(f"✅ Generated audio for {len(audio_results)} sections!")
            
            # Display audio players for each section
            display_audio_players(audio_results, session_id)
            
    except Exception as e:
        st.error(f"❌ Error generating audio: {str(e)}")
        logger.error(f"Audio generation error: {str(e)}")

def display_audio_players(audio_results, session_id):
    """Display audio players for generated content"""
    
    st.markdown("#### 🎧 Your Personalized Audio Content")
    
    # Section descriptions
    section_descriptions = {
        "style_analysis": "🎯 Your Style Analysis - Complete breakdown of your style personality",
        "recommendations": "👗 Style Recommendations - Detailed explanation of suggested items", 
        "color_analysis": "🎨 Color Analysis - Your perfect color palette explained",
        "confidence_boost": "💪 Confidence Boost - Positive affirmations about your style",
        "shopping_guide": "🛍️ Shopping Guide - Practical advice for your next shopping trip"
    }
    
    for section_name, audio_result in audio_results.items():
        # Create section header
        description = section_descriptions.get(section_name, f"📻 {section_name.replace('_', ' ').title()}")
        st.markdown(f"##### {description}")
        
        # Show audio info
        duration = audio_result.get('estimated_duration', 0)
        size_kb = audio_result.get('size_bytes', 0) // 1024
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.info(f"Duration: ~{duration} seconds")
        with col2:
            st.info(f"Size: {size_kb} KB")
        with col3:
            st.info(f"Voice: {audio_result.get('voice_id', 'Joanna')}")
        
        # Create temporary file for audio playback
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(audio_result['audio_data'])
                tmp_file_path = tmp_file.name
            
            # Display audio player
            with open(tmp_file_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                st.audio(audio_bytes, format='audio/mp3')
            
            # Download button
            st.download_button(
                label=f"📥 Download {section_name.replace('_', ' ').title()}",
                data=audio_result['audio_data'],
                file_name=f"essencemirror_{section_name}_{session_id[:8]}.mp3",
                mime="audio/mpeg"
            )
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
        except Exception as e:
            st.error(f"Error displaying audio for {section_name}: {str(e)}")
        
        st.markdown("---")
    
    # Summary and tips
    st.markdown("#### 💡 How to Use Your Audio Content")
    st.info("""
    **💡 Tips for your audio content:**
    - 🎧 **Listen while getting ready** - Perfect morning routine companion
    - 🛍️ **Take shopping** - Download and listen while browsing stores  
    - 💪 **Daily confidence boost** - Listen to affirmations anytime
    - 📱 **Share with friends** - Get their opinions on your style insights
    - 🔄 **Replay anytime** - Your personal style coach available 24/7
    """)

def test_audio_component():
    """Test function for the audio component"""
    st.markdown("### 🧪 Audio Component Test")
    
    if AUDIO_GENERATOR_AVAILABLE:
        st.success("✅ Audio generator is available")
        
        # Test with sample data
        sample_data = {
            "analysis": "Your style shows sophisticated elegance with modern touches",
            "recommendations": ["tailored blazer", "elegant dress", "classic accessories"]
        }
        
        if st.button("🧪 Test Audio Generation"):
            generate_audio_content(sample_data, "joanna", "test_session")
    else:
        st.error("❌ Audio generator not available")

# Main function for standalone testing
def main():
    """Main function for testing the component"""
    st.set_page_config(
        page_title="EssenceMirror Audio Test",
        page_icon="🎵",
        layout="wide"
    )
    
    st.title("🎵 EssenceMirror Audio Component Test")
    
    # Test the component
    test_audio_component()
    
    # Full component test
    st.markdown("---")
    render_audio_style_tab(
        session_id="test_session_123",
        analysis_complete=True,
        style_analysis_data=None  # Will use sample data
    )

if __name__ == "__main__":
    main()
