"""
Style Reel Component for EssenceMirror Streamlit App
Integrates image-inspired video generation using Nova Reel
"""

import streamlit as st
import os
import sys
import json
import time
import uuid
import tempfile
from datetime import datetime
from PIL import Image
import logging

# Add the infrastructure directory to the path to import our generators
sys.path.append('/Users/kirubelaklilu/Documents/EssenceMirror/essence-mirror-infrastructure')

try:
    from image_inspired_generator import (
        create_image_inspired_prompt, 
        simulate_style_analysis, 
        extract_style_elements,
        analyze_image_basic
    )
    from nova_reel_generator import NovaReelGenerator
except ImportError as e:
    st.error(f"Error importing video generation modules: {str(e)}")
    st.info("Make sure the infrastructure components are properly set up.")

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = "essencemirror-user-uploads"

def save_uploaded_file_temporarily(uploaded_file):
    """Save uploaded file to a temporary location for processing"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        logger.error(f"Error saving temporary file: {str(e)}")
        return None

def generate_style_video(image_path, user_prompt=None, style_focus="lifestyle", duration=6):
    """Generate a style video using the image-inspired approach"""
    try:
        # Simulate style analysis (in production, this would come from the actual analysis)
        style_analysis = simulate_style_analysis()
        
        # Extract style elements
        style_elements = extract_style_elements(style_analysis)
        
        # Enhance style elements based on focus
        focus_enhancements = {
            "wardrobe": ["fashion-forward", "stylish clothing", "trendy outfits"],
            "interior": ["home decor", "interior design", "living space aesthetics"],
            "travel": ["wanderlust", "travel destinations", "adventure scenes"],
            "lifestyle": ["daily life", "personal moments", "lifestyle photography"]
        }
        
        if style_focus in focus_enhancements:
            style_elements.extend(focus_enhancements[style_focus])
        
        # Create image-inspired prompt
        final_prompt, image_analysis = create_image_inspired_prompt(
            image_path, user_prompt, style_elements
        )
        
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize the Nova Reel Generator
        nova_reel = NovaReelGenerator(s3_bucket=S3_BUCKET)
        
        logger.info(f"Generating style video with prompt: {final_prompt}")
        
        # Generate video using text-to-video with the image-inspired prompt
        result = nova_reel.generate_style_reel(
            user_id=job_id,
            prompt=final_prompt,
            style_elements=[],  # Already included in final_prompt
            duration_seconds=duration
        )
        
        # Return the job information with image context
        return {
            "jobId": job_id,
            "videoJobId": result["job_id"],
            "status": "VIDEO_GENERATION_STARTED",
            "timestamp": datetime.utcnow().isoformat(),
            "inputType": "image-inspired",
            "inputImage": image_path,
            "originalPrompt": user_prompt,
            "finalPrompt": final_prompt,
            "imageAnalysis": image_analysis,
            "styleFocus": style_focus,
            "duration": duration
        }
        
    except Exception as e:
        logger.error(f"Error generating style video: {str(e)}")
        raise

def check_video_status(job_info):
    """Check the status of a video generation job"""
    try:
        # Initialize the Nova Reel Generator
        nova_reel = NovaReelGenerator(s3_bucket=S3_BUCKET)
        
        # Check the status of the video generation job
        video_job_id = job_info["videoJobId"]
        
        status_result = nova_reel.check_job_status(video_job_id)
        job_status = status_result.get("status")
        
        if job_status == "Completed":
            # Job completed successfully
            video_url = status_result.get("video_url")
            
            # Update job status
            job_info["status"] = "VIDEO_GENERATED"
            job_info["videoUrl"] = video_url
            job_info["updatedAt"] = datetime.utcnow().isoformat()
            
        elif job_status == "Failed":
            # Job failed
            failure_message = status_result.get("message", "Unknown failure")
            
            # Update job status
            job_info["status"] = "VIDEO_GENERATION_FAILED"
            job_info["errorMessage"] = failure_message
            job_info["updatedAt"] = datetime.utcnow().isoformat()
            
        else:
            # Job still in progress
            job_info["status"] = "VIDEO_GENERATION_IN_PROGRESS"
            job_info["updatedAt"] = datetime.utcnow().isoformat()
        
        return job_info
        
    except Exception as e:
        logger.error(f"Error checking video status: {str(e)}")
        job_info["status"] = "ERROR"
        job_info["errorMessage"] = str(e)
        job_info["updatedAt"] = datetime.utcnow().isoformat()
        return job_info

def render_style_reel_tab(session_id, analysis_complete):
    """Render the Style Reel tab content"""
    
    st.markdown("### 🎬 Style in Motion (Beta)")
    st.markdown("Transform your style into dynamic videos using AI! Upload an image and watch your personal aesthetic come to life.")
    
    # Initialize session state for video generation
    if 'video_job' not in st.session_state:
        st.session_state.video_job = None
    if 'video_generation_in_progress' not in st.session_state:
        st.session_state.video_generation_in_progress = False
    if 'generated_video_url' not in st.session_state:
        st.session_state.generated_video_url = None
    
    # Two columns layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📸 Upload Image for Video")
        
        # Image uploader for video generation
        video_image = st.file_uploader(
            "Choose an image for your style video",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image that represents your style - this will inspire the video generation",
            key="video_image_uploader"
        )
        
        if video_image is not None:
            # Display uploaded image
            st.image(video_image, caption="Your style inspiration", use_column_width=True)
            
            # Video generation options
            st.markdown("#### 🎯 Video Options")
            
            # Style focus selection
            style_focus_options = {
                "lifestyle": "🌟 Complete Lifestyle",
                "wardrobe": "👗 Fashion & Wardrobe",
                "interior": "🏠 Home & Interior",
                "travel": "✈️ Travel & Adventure"
            }
            
            selected_focus = st.selectbox(
                "Video Focus:",
                options=list(style_focus_options.keys()),
                format_func=lambda x: style_focus_options[x],
                index=0,
                key="video_style_focus"
            )
            
            # Duration selection
            duration = st.slider(
                "Video Duration (seconds):",
                min_value=5,
                max_value=15,
                value=8,
                step=1,
                key="video_duration"
            )
            
            # Optional text prompt
            user_prompt = st.text_area(
                "Additional Description (Optional):",
                placeholder="e.g., 'elegant and sophisticated', 'vibrant and energetic', 'minimalist and clean'",
                help="Add specific words to guide the video style",
                key="video_text_prompt"
            )
            
            # Generate video button
            if not st.session_state.video_generation_in_progress:
                if st.button("🎬 Generate Style Video", type="primary", key="generate_video_btn"):
                    # Save uploaded file temporarily
                    temp_image_path = save_uploaded_file_temporarily(video_image)
                    
                    if temp_image_path:
                        try:
                            with st.spinner("🎬 Creating your style video... This may take 2-3 minutes."):
                                # Generate the video
                                job_info = generate_style_video(
                                    image_path=temp_image_path,
                                    user_prompt=user_prompt if user_prompt.strip() else None,
                                    style_focus=selected_focus,
                                    duration=duration
                                )
                                
                                # Store job info in session state
                                st.session_state.video_job = job_info
                                st.session_state.video_generation_in_progress = True
                                
                                st.success("🎉 Video generation started! Please wait while we create your style video.")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error starting video generation: {str(e)}")
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_image_path)
                            except:
                                pass
                    else:
                        st.error("Error processing uploaded image. Please try again.")
            else:
                st.info("🎬 Video generation in progress... Please wait.")
                
                # Show progress and check status
                if st.session_state.video_job:
                    # Status checking
                    if st.button("🔄 Check Status", key="check_video_status"):
                        with st.spinner("Checking video generation status..."):
                            updated_job = check_video_status(st.session_state.video_job)
                            st.session_state.video_job = updated_job
                            
                            if updated_job["status"] == "VIDEO_GENERATED":
                                st.session_state.video_generation_in_progress = False
                                st.session_state.generated_video_url = updated_job["videoUrl"]
                                st.success("🎉 Your style video is ready!")
                                st.rerun()
                            elif updated_job["status"] == "VIDEO_GENERATION_FAILED":
                                st.session_state.video_generation_in_progress = False
                                st.error(f"Video generation failed: {updated_job.get('errorMessage', 'Unknown error')}")
                            elif updated_job["status"] == "ERROR":
                                st.session_state.video_generation_in_progress = False
                                st.error(f"Error: {updated_job.get('errorMessage', 'Unknown error')}")
                    
                    # Auto-refresh every 15 seconds
                    time.sleep(1)  # Small delay to prevent too frequent updates
    
    with col2:
        st.markdown("#### 🎥 Generated Style Video")
        
        # Display generated video if available
        if st.session_state.generated_video_url:
            st.markdown("##### ✨ Your Style Video is Ready!")
            
            # Display video information
            if st.session_state.video_job:
                job = st.session_state.video_job
                
                # Video details
                with st.expander("📋 Video Details", expanded=False):
                    st.write(f"**Style Focus:** {style_focus_options.get(job.get('styleFocus', 'lifestyle'), 'Lifestyle')}")
                    st.write(f"**Duration:** {job.get('duration', 6)} seconds")
                    if job.get('originalPrompt'):
                        st.write(f"**Your Prompt:** {job['originalPrompt']}")
                    st.write(f"**AI-Generated Prompt:** {job.get('finalPrompt', 'N/A')}")
                    st.write(f"**Generated:** {job.get('timestamp', 'N/A')}")
            
            # Video display options
            st.markdown("**🎬 Watch Your Video:**")
            
            # Try to display video directly (this might not work for S3 URLs)
            try:
                st.video(st.session_state.generated_video_url)
            except Exception as e:
                # Fallback to download link
                st.markdown(f"[🔗 **Download Your Style Video**]({st.session_state.generated_video_url})")
                st.info("Click the link above to download and view your style video.")
            
            # Action buttons
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("🔄 Generate New", key="generate_new_video"):
                    # Reset video generation state
                    st.session_state.video_job = None
                    st.session_state.video_generation_in_progress = False
                    st.session_state.generated_video_url = None
                    st.rerun()
            
            with col_b:
                st.markdown(f"[📥 Download]({st.session_state.generated_video_url})")
            
            with col_c:
                if st.button("📋 Copy Link", key="copy_video_link"):
                    st.code(st.session_state.generated_video_url)
                    st.success("Link copied to display!")
        
        elif st.session_state.video_generation_in_progress:
            # Show progress
            st.markdown("##### 🎬 Generating Your Style Video...")
            
            if st.session_state.video_job:
                job = st.session_state.video_job
                
                # Progress information
                st.info(f"**Status:** {job.get('status', 'Unknown')}")
                st.info(f"**Job ID:** {job.get('jobId', 'N/A')[:8]}...")
                
                # Show what's being generated
                st.markdown("**🎯 Video Details:**")
                st.write(f"• **Focus:** {style_focus_options.get(job.get('styleFocus', 'lifestyle'), 'Lifestyle')}")
                st.write(f"• **Duration:** {job.get('duration', 6)} seconds")
                if job.get('originalPrompt'):
                    st.write(f"• **Your Input:** {job['originalPrompt']}")
                
                # Estimated time
                st.markdown("⏱️ **Estimated Time:** 2-3 minutes")
                
                # Progress bar (simulated)
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
        
        else:
            # Instructions
            st.info("👈 Upload an image and configure your video options to get started!")
            
            st.markdown("##### 🌟 How it works:")
            st.markdown("""
            1. **📸 Upload Image**: Choose a photo that represents your style
            2. **🎯 Select Focus**: Pick what aspect of your lifestyle to highlight
            3. **⏱️ Set Duration**: Choose video length (5-15 seconds)
            4. **✍️ Add Description**: Optional text to guide the style
            5. **🎬 Generate**: AI creates a personalized style video
            """)
            
            st.markdown("##### ✨ Features:")
            st.markdown("""
            - **AI-Powered**: Uses Amazon Nova Reel for video generation
            - **Style-Aware**: Analyzes your image to understand your aesthetic
            - **Customizable**: Multiple focus areas and duration options
            - **High Quality**: Professional-looking style videos
            """)
    
    # Footer for the tab
    st.markdown("---")
    st.markdown("*🎬 Style in Motion powered by Amazon Nova Reel - Transform your style into dynamic videos*")

# Additional utility functions
def cleanup_temp_files():
    """Clean up any temporary files that might be left over"""
    try:
        temp_dir = tempfile.gettempdir()
        # Clean up old temporary files (implementation depends on your needs)
        pass
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")

def get_video_thumbnail(video_url):
    """Generate a thumbnail for the video (placeholder for future implementation)"""
    # This could be implemented to generate thumbnails from videos
    # For now, return None
    return None
