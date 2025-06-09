"""
Style Reel Component for EssenceMirror
This module handles the UI components for the Style Reel feature.
"""

import streamlit as st
import base64
import time
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def render_style_reel_tab(session_id, analysis_complete=False):
    """Render the Style Reel tab in the Streamlit app"""
    
    st.markdown("### 🎬 Style in Motion (Beta)")
    
    if not analysis_complete:
        st.info("👆 Upload and analyze an image first to create your personalized style video!")
        return
    
    st.markdown("""
    Transform your style profile into a dynamic video experience! 
    Our AI will create a personalized style reel that brings your unique aesthetic to life.
    """)
    
    # Beta badge
    st.markdown(
        """
        <div style="display: inline-block; background-color: #FF4B4B; color: white; padding: 0.2rem 0.6rem; 
        border-radius: 0.5rem; font-size: 0.8rem; margin-bottom: 1rem;">
        BETA FEATURE
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Category selection
    reel_categories = {
        "wardrobe": "👗 Wardrobe & Fashion",
        "interior": "🏠 Home & Interior Design", 
        "travel": "✈️ Travel & Experiences",
        "lifestyle": "🌟 Complete Lifestyle"
    }
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        selected_category = st.selectbox(
            "Select video focus:",
            options=list(reel_categories.keys()),
            format_func=lambda x: reel_categories[x],
            index=0,
            key="reel_category"
        )
    
    with col2:
        use_original_image = st.checkbox("Include my uploaded image", value=True, 
                                        help="Use your uploaded image as reference in the style video")
    
    # Advanced options expander
    with st.expander("Advanced Options"):
        duration_seconds = st.slider("Video Duration (seconds)", min_value=5, max_value=15, value=10, step=1)
    
    # Style reel generation button
    if st.button(f"🎬 Generate {reel_categories[selected_category]} Video", type="primary"):
        with st.spinner(f"Creating your personalized {reel_categories[selected_category].lower()} video... This may take up to a minute."):
            try:
                # Start timer for UX feedback
                start_time = time.time()
                
                # Generate the style reel
                reel_result = generate_style_reel(
                    session_id, 
                    selected_category, 
                    use_original_image,
                    duration_seconds
                )
                
                generation_time = time.time() - start_time
                
                if reel_result:
                    st.session_state.reel_data = reel_result
                    st.session_state.reel_category = selected_category
                    st.success(f"🎉 Your {reel_categories[selected_category].lower()} video is ready! (Generated in {generation_time:.1f}s)")
                    st.rerun()
                else:
                    st.error("Sorry, we couldn't generate your style video. Please try again.")
            except Exception as e:
                logger.error(f"Error generating style reel: {str(e)}")
                st.error(f"An error occurred: {str(e)}")
    
    # Display generated video
    if hasattr(st.session_state, 'reel_data') and st.session_state.reel_data:
        category_name = reel_categories.get(st.session_state.get('reel_category', 'lifestyle'), 'Style')
        st.markdown(f"#### 🎬 Your {category_name} Video:")
        
        # Try to display the video
        video_displayed = False
        
        # Method 1: Try URL if available
        if 'video_url' in st.session_state.reel_data:
            try:
                video_url = st.session_state.reel_data['video_url']
                st.video(video_url)
                video_displayed = True
                st.markdown(f"*Video URL: [Open in new tab]({video_url})*")
            except Exception as e:
                logger.error(f"Error displaying video from URL: {str(e)}")
        
        # Method 2: Try base64 if available and URL failed
        if not video_displayed and 'video_base64' in st.session_state.reel_data:
            try:
                video_data = base64.b64decode(st.session_state.reel_data['video_base64'])
                
                # Save to a temporary file
                temp_file = "temp_video.mp4"
                with open(temp_file, "wb") as f:
                    f.write(video_data)
                
                # Display the video
                st.video(temp_file)
                video_displayed = True
            except Exception as e:
                logger.error(f"Error displaying video from base64: {str(e)}")
        
        if not video_displayed:
            st.error("Unable to display the video. Please try generating it again.")
        
        # Display the prompt used (for troubleshooting)
        if 'prompt_used' in st.session_state.reel_data:
            with st.expander("🔍 View Prompt Used"):
                st.text_area("Prompt for Nova Reel", 
                            st.session_state.reel_data['prompt_used'], 
                            height=200)

def generate_style_reel(session_id, category="lifestyle", use_original_image=True, duration_seconds=10):
    """Generate a style reel video using Nova Reel"""
    try:
        # Import clients from the main app
        from essence_mirror_app import clients
        
        # Call the Lambda function for Nova Reel
        event = {
            "messageVersion": "1.0",
            "sessionId": session_id,
            "actionGroup": "EssenceMirrorActions",
            "httpMethod": "POST",
            "apiPath": "/generateStyleReel",
            "requestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {
                                "name": "style_focus",
                                "value": category
                            },
                            {
                                "name": "use_original_image",
                                "value": use_original_image
                            },
                            {
                                "name": "duration_seconds",
                                "value": duration_seconds
                            }
                        ]
                    }
                }
            }
        }
        
        logger.info(f"Calling Lambda for style reel generation with category: {category}")
        
        lambda_response = clients['lambda'].invoke(
            FunctionName='essenceMirror',
            Payload=json.dumps(event)
        )
        
        response_payload = json.loads(lambda_response['Payload'].read())
        
        if 'response' in response_payload and 'responseBody' in response_payload['response']:
            response_body = response_payload['response']['responseBody']
            if 'application/json' in response_body:
                body_content = json.loads(response_body['application/json']['body'])
                
                # Return video data and metadata
                result = {}
                if 'video_url' in body_content:
                    result['video_url'] = body_content['video_url']
                if 'video_base64' in body_content:
                    result['video_base64'] = body_content['video_base64']
                if 'prompt_used' in body_content:
                    result['prompt_used'] = body_content['prompt_used']
                
                if result:
                    logger.info(f"Successfully generated style reel for category: {category}")
                    return result
        
        logger.error("Failed to generate style reel: Invalid response format")
        return None
        
    except Exception as e:
        logger.error(f"Error generating style reel: {str(e)}")
        return None
