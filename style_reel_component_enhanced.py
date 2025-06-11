"""
Enhanced Style Reel Component for EssenceMirror Streamlit App
Uses advanced image analysis to create videos that closely match uploaded images
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

# Add the infrastructure directory to the path
sys.path.append('/Users/kirubelaklilu/Documents/EssenceMirror/essence-mirror-infrastructure')

try:
    from enhanced_image_video_generator import EnhancedImageVideoGenerator
    from nova_reel_generator_fixed import NovaReelGenerator
except ImportError as e:
    st.error(f"Error importing enhanced video generation modules: {str(e)}")
    st.info("Make sure the enhanced infrastructure components are properly set up.")

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

def generate_enhanced_style_video(image_path, user_prompt=None, style_focus="lifestyle"):
    """Generate an enhanced style video that closely matches the uploaded image"""
    try:
        # Initialize the enhanced generator
        generator = EnhancedImageVideoGenerator(s3_bucket=S3_BUCKET)
        
        # Enhance style elements based on focus
        focus_enhancements = {
            "wardrobe": ["fashion-forward styling", "elegant clothing", "sophisticated wardrobe choices"],
            "interior": ["interior design elements", "home aesthetics", "living space ambiance"],
            "travel": ["wanderlust atmosphere", "travel destinations", "adventure cinematography"],
            "lifestyle": ["lifestyle photography", "personal moments", "daily life aesthetics"]
        }
        
        style_elements = focus_enhancements.get(style_focus, ["lifestyle aesthetics"])
        
        # Generate enhanced video
        result = generator.generate_enhanced_video(
            image_path=image_path,
            user_prompt=user_prompt,
            style_elements=style_elements,
            user_id=str(uuid.uuid4())
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating enhanced style video: {str(e)}")
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
    """Render the enhanced Style Reel tab content"""
    
    st.markdown("### 🎬 Enhanced Style Videos")
    st.markdown("Upload an image and create videos that closely match its visual characteristics using advanced AI analysis!")
    
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
        st.markdown("#### 📸 Upload Image for Enhanced Video")
        
        # Image uploader for video generation
        video_image = st.file_uploader(
            "Choose an image for your style video",
            type=['png', 'jpg', 'jpeg', 'webp'],
            help="Upload an image - AI will analyze its colors, composition, lighting, and content to create a matching video",
            key="enhanced_video_image_uploader"
        )
        
        if video_image is not None:
            # Display uploaded image
            st.image(video_image, caption="Your style inspiration", use_column_width=True)
            
            # Show what will be analyzed
            with st.expander("🔍 What AI Will Analyze"):
                st.markdown("""
                **Advanced Image Analysis:**
                - 🎨 **Color Palette**: Dominant colors, temperature, saturation
                - 📐 **Composition**: Framing, focal points, rule of thirds
                - 💡 **Lighting**: Brightness, contrast, mood
                - 🖼️ **Content**: Subject matter, style elements
                - 🎬 **Cinematic Qualities**: How to translate to video
                """)
            
            # Video generation options
            st.markdown("#### 🎯 Enhanced Video Options")
            
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
                key="enhanced_video_style_focus"
            )
            
            # Duration info (fixed at 6 seconds)
            st.info("ℹ️ Video duration: 6 seconds (optimized for Nova Reel)")
            
            # Optional text prompt
            user_prompt = st.text_area(
                "Additional Style Description (Optional):",
                placeholder="e.g., 'elegant movement', 'serene atmosphere', 'dynamic energy'",
                help="Add specific words to enhance the video style beyond what's detected from your image",
                key="enhanced_video_text_prompt"
            )
            
            # Generate video button
            if not st.session_state.video_generation_in_progress:
                if st.button("🎬 Generate Enhanced Style Video", type="primary", key="generate_enhanced_video_btn"):
                    # Save uploaded file temporarily
                    temp_image_path = save_uploaded_file_temporarily(video_image)
                    
                    if temp_image_path:
                        try:
                            with st.spinner("🎬 Analyzing your image and creating enhanced style video... This may take 2-3 minutes."):
                                # Generate the enhanced video
                                result = generate_enhanced_style_video(
                                    image_path=temp_image_path,
                                    user_prompt=user_prompt if user_prompt.strip() else None,
                                    style_focus=selected_focus
                                )
                                
                                # Store job info in session state
                                job_info = {
                                    "jobId": result["user_id"],
                                    "videoJobId": result["job_id"],
                                    "status": "VIDEO_GENERATION_STARTED",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "inputType": "enhanced-image-analysis",
                                    "inputImage": temp_image_path,
                                    "originalPrompt": user_prompt,
                                    "enhancedPrompt": result.get("enhanced_prompt"),
                                    "imageAnalysis": result.get("image_analysis"),
                                    "styleFocus": selected_focus,
                                    "duration": 6
                                }
                                
                                st.session_state.video_job = job_info
                                st.session_state.video_generation_in_progress = True
                                
                                st.success("🎉 Enhanced video generation started! AI analyzed your image in detail.")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error starting enhanced video generation: {str(e)}")
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_image_path)
                            except:
                                pass
                    else:
                        st.error("Error processing uploaded image. Please try again.")
            else:
                st.info("🎬 Enhanced video generation in progress... Please wait.")
                
                # Show progress and check status
                if st.session_state.video_job:
                    # Status checking
                    if st.button("🔄 Check Status", key="check_enhanced_video_status"):
                        with st.spinner("Checking enhanced video generation status..."):
                            updated_job = check_video_status(st.session_state.video_job)
                            st.session_state.video_job = updated_job
                            
                            if updated_job["status"] == "VIDEO_GENERATED":
                                st.session_state.video_generation_in_progress = False
                                st.session_state.generated_video_url = updated_job["videoUrl"]
                                st.success("🎉 Your enhanced style video is ready!")
                                st.rerun()
                            elif updated_job["status"] == "VIDEO_GENERATION_FAILED":
                                st.session_state.video_generation_in_progress = False
                                st.error(f"Enhanced video generation failed: {updated_job.get('errorMessage', 'Unknown error')}")
                            elif updated_job["status"] == "ERROR":
                                st.session_state.video_generation_in_progress = False
                                st.error(f"Error: {updated_job.get('errorMessage', 'Unknown error')}")
    
    with col2:
        st.markdown("#### 🎥 Enhanced Style Video Results")
        
        # Display generated video if available
        if st.session_state.generated_video_url:
            st.markdown("##### ✨ Your Enhanced Style Video is Ready!")
            
            # Display video information
            if st.session_state.video_job:
                job = st.session_state.video_job
                
                # Enhanced video details
                with st.expander("📋 Enhanced Video Details", expanded=True):
                    st.write(f"**Style Focus:** {style_focus_options.get(job.get('styleFocus', 'lifestyle'), 'Lifestyle')}")
                    st.write(f"**Duration:** {job.get('duration', 6)} seconds")
                    
                    if job.get('originalPrompt'):
                        st.write(f"**Your Input:** {job['originalPrompt']}")
                    
                    if job.get('enhancedPrompt'):
                        st.write(f"**AI-Enhanced Prompt:**")
                        st.text_area("Generated from your image analysis:", job['enhancedPrompt'], height=100, key="enhanced_prompt_display")
                    
                    # Show image analysis results
                    if job.get('imageAnalysis'):
                        analysis = job['imageAnalysis']
                        st.write("**🔍 Image Analysis Results:**")
                        
                        if analysis.get('colors', {}).get('palette_description'):
                            st.write(f"• **Colors:** {analysis['colors']['palette_description']}")
                        
                        if analysis.get('composition'):
                            st.write(f"• **Composition:** {analysis['composition']}")
                        
                        if analysis.get('lighting'):
                            st.write(f"• **Lighting:** {analysis['lighting']}")
                        
                        if analysis.get('content'):
                            st.write(f"• **Content:** {', '.join(analysis['content'][:3])}")
                    
                    st.write(f"**Generated:** {job.get('timestamp', 'N/A')}")
            
            # Video display options
            st.markdown("**🎬 Watch Your Enhanced Video:**")
            
            # Try to display video directly
            try:
                st.video(st.session_state.generated_video_url)
            except Exception as e:
                # Fallback to download link
                st.markdown(f"[🔗 **Download Your Enhanced Style Video**]({st.session_state.generated_video_url})")
                st.info("Click the link above to download and view your enhanced style video.")
            
            # Action buttons
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("🔄 Generate New", key="generate_new_enhanced_video"):
                    # Reset video generation state
                    st.session_state.video_job = None
                    st.session_state.video_generation_in_progress = False
                    st.session_state.generated_video_url = None
                    st.rerun()
            
            with col_b:
                st.markdown(f"[📥 Download]({st.session_state.generated_video_url})")
            
            with col_c:
                if st.button("📋 Copy Link", key="copy_enhanced_video_link"):
                    st.code(st.session_state.generated_video_url)
                    st.success("Link copied to display!")
        
        elif st.session_state.video_generation_in_progress:
            # Show progress
            st.markdown("##### 🎬 Creating Your Enhanced Style Video...")
            
            if st.session_state.video_job:
                job = st.session_state.video_job
                
                # Progress information
                st.info(f"**Status:** {job.get('status', 'Unknown')}")
                st.info(f"**Job ID:** {job.get('jobId', 'N/A')[:8]}...")
                
                # Show what's being generated
                st.markdown("**🎯 Enhanced Video Details:**")
                st.write(f"• **Focus:** {style_focus_options.get(job.get('styleFocus', 'lifestyle'), 'Lifestyle')}")
                st.write(f"• **Duration:** {job.get('duration', 6)} seconds")
                st.write(f"• **Method:** Advanced image analysis + AI generation")
                
                if job.get('enhancedPrompt'):
                    with st.expander("🔍 View AI-Generated Prompt"):
                        st.text_area("Enhanced prompt from your image:", job['enhancedPrompt'], height=100, key="progress_prompt_display")
                
                # Estimated time
                st.markdown("⏱️ **Estimated Time:** 2-3 minutes")
                
                # Progress bar (simulated)
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
        
        else:
            # Instructions
            st.info("👈 Upload an image to create enhanced style videos!")
            
            st.markdown("##### 🌟 Enhanced Video Generation:")
            st.markdown("""
            **🔍 Advanced AI Analysis:**
            - Analyzes your image's colors, lighting, and composition
            - Identifies visual style and aesthetic elements  
            - Recognizes content and subject matter
            
            **🎬 Smart Video Creation:**
            - Generates videos that match your image's visual characteristics
            - Preserves color palette and lighting mood
            - Maintains compositional style and framing
            - Creates cinematic movement that complements your image
            
            **✨ Result:**
            Videos that truly reflect your personal style and aesthetic!
            """)
            
            st.markdown("##### 🎯 Best Results:")
            st.markdown("""
            - **Clear, well-lit photos** work best
            - **Strong visual style** gets better analysis
            - **Good composition** translates well to video
            - **Distinctive colors** are preserved in the video
            """)
    
    # Footer for the tab
    st.markdown("---")
    st.markdown("*🎬 Enhanced Style Videos powered by Advanced Image Analysis + Amazon Nova Reel*")
    st.markdown("**🚀 New:** Videos now closely match your image's colors, lighting, composition, and style!")
