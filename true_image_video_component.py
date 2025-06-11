"""
True Image-to-Video Component for EssenceMirror Streamlit App
Shows the ACTUAL uploaded user wearing recommended styles in generated videos
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
    from true_image_to_video_generator import TrueImageToVideoGenerator
except ImportError as e:
    st.error(f"Error importing true image-to-video modules: {str(e)}")
    st.info("Make sure the true image-to-video components are properly set up.")

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

def generate_personalized_recommendation_video(image_path, style_focus, specific_recommendations=None, user_id=None):
    """Generate a video showing the actual user wearing recommended styles"""
    try:
        # Initialize the true image-to-video generator with environment credentials
        generator = TrueImageToVideoGenerator(s3_bucket=S3_BUCKET, profile_name=None)
        
        # Generate personalized video
        result = generator.generate_style_recommendation_video(
            image_path=image_path,
            style_focus=style_focus,
            specific_recommendations=specific_recommendations,
            user_id=user_id or str(uuid.uuid4())
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating personalized recommendation video: {str(e)}")
        raise

def check_video_status(job_info):
    """Check the status of a video generation job"""
    try:
        # Initialize the generator for status checking with environment credentials
        generator = TrueImageToVideoGenerator(s3_bucket=S3_BUCKET, profile_name=None)
        
        # Check the status of the video generation job
        video_job_id = job_info["videoJobId"]
        
        status_result = generator.check_job_status(video_job_id)
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

def render_true_image_video_tab(session_id, analysis_complete):
    """Render the True Image-to-Video tab content"""
    
    st.markdown("### 🎬 Personalized Style Videos")
    st.markdown("**BREAKTHROUGH**: Upload your photo and see **yourself** wearing recommended styles in AI-generated videos!")
    
    # Highlight the breakthrough
    st.success("🎉 **NEW**: Nova Reel now shows the ACTUAL uploaded person in videos - not just generic people!")
    
    # Initialize session state for video generation
    if 'personalized_video_job' not in st.session_state:
        st.session_state.personalized_video_job = None
    if 'personalized_video_in_progress' not in st.session_state:
        st.session_state.personalized_video_in_progress = False
    if 'personalized_video_url' not in st.session_state:
        st.session_state.personalized_video_url = None
    
    # Two columns layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📸 Upload Your Photo")
        
        # Image uploader for personalized video generation
        user_image = st.file_uploader(
            "Upload your photo to see yourself in recommended styles",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo of yourself - you'll see YOURSELF wearing the recommended styles in the video!",
            key="personalized_video_uploader"
        )
        
        if user_image is not None:
            # Display uploaded image
            st.image(user_image, caption="You will appear in the video!", use_column_width=True)
            
            # Show what will happen
            st.info("🎯 **What happens**: AI will show YOU wearing the recommended styles while maintaining your facial features and body type!")
            
            # Video generation options
            st.markdown("#### 🎯 Personalized Recommendation Options")
            
            # Style focus selection
            style_focus_options = {
                "wardrobe": "👗 Fashion & Wardrobe",
                "lifestyle": "🌟 Complete Lifestyle",
                "interior": "🏠 Home & Interior Settings",
                "travel": "✈️ Travel & Adventure Looks"
            }
            
            selected_focus = st.selectbox(
                "What style recommendations do you want to see yourself wearing?",
                options=list(style_focus_options.keys()),
                format_func=lambda x: style_focus_options[x],
                index=0,
                key="personalized_style_focus"
            )
            
            # Specific recommendations input
            specific_recs = st.text_area(
                "Specific Style Recommendations (Optional):",
                placeholder="e.g., 'tailored blazers, elegant dresses, modern accessories'",
                help="Add specific items you want to see yourself wearing",
                key="specific_recommendations"
            )
            
            # Parse specific recommendations
            recommendations_list = None
            if specific_recs.strip():
                recommendations_list = [item.strip() for item in specific_recs.split(',') if item.strip()]
            
            # Duration info
            st.info("ℹ️ Video duration: 6 seconds showing your personalized style transformation")
            
            # Generate personalized video button
            if not st.session_state.personalized_video_in_progress:
                if st.button("🎬 Generate My Personalized Style Video", type="primary", key="generate_personalized_btn"):
                    # Save uploaded file temporarily
                    temp_image_path = save_uploaded_file_temporarily(user_image)
                    
                    if temp_image_path:
                        try:
                            with st.spinner("🎬 Creating your personalized style video... You'll see YOURSELF wearing the recommended styles! This may take 2-3 minutes."):
                                # Generate the personalized video
                                result = generate_personalized_recommendation_video(
                                    image_path=temp_image_path,
                                    style_focus=selected_focus,
                                    specific_recommendations=recommendations_list,
                                    user_id=session_id
                                )
                                
                                # Store job info in session state
                                job_info = {
                                    "jobId": result["user_id"],
                                    "videoJobId": result["job_id"],
                                    "status": "VIDEO_GENERATION_STARTED",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "inputType": "true_personalized_video",
                                    "inputImage": temp_image_path,
                                    "styleFocus": selected_focus,
                                    "specificRecommendations": recommendations_list,
                                    "personalizedPrompt": result.get("prompt"),
                                    "duration": 6,
                                    "method": "true_image_to_video"
                                }
                                
                                st.session_state.personalized_video_job = job_info
                                st.session_state.personalized_video_in_progress = True
                                
                                st.success("🎉 Your personalized style video is being created! You'll see yourself wearing the recommended styles.")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error starting personalized video generation: {str(e)}")
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_image_path)
                            except:
                                pass
                    else:
                        st.error("Error processing uploaded image. Please try again.")
            else:
                st.info("🎬 Your personalized video is being created... Please wait.")
                
                # Show progress and check status
                if st.session_state.personalized_video_job:
                    # Status checking
                    if st.button("🔄 Check Status", key="check_personalized_status"):
                        with st.spinner("Checking your personalized video status..."):
                            updated_job = check_video_status(st.session_state.personalized_video_job)
                            st.session_state.personalized_video_job = updated_job
                            
                            if updated_job["status"] == "VIDEO_GENERATED":
                                st.session_state.personalized_video_in_progress = False
                                st.session_state.personalized_video_url = updated_job["videoUrl"]
                                st.success("🎉 Your personalized style video is ready! You can see yourself wearing the recommended styles!")
                                st.rerun()
                            elif updated_job["status"] == "VIDEO_GENERATION_FAILED":
                                st.session_state.personalized_video_in_progress = False
                                st.error(f"Personalized video generation failed: {updated_job.get('errorMessage', 'Unknown error')}")
                            elif updated_job["status"] == "ERROR":
                                st.session_state.personalized_video_in_progress = False
                                st.error(f"Error: {updated_job.get('errorMessage', 'Unknown error')}")
    
    with col2:
        st.markdown("#### 🎥 Your Personalized Style Video")
        
        # Display generated video if available
        if st.session_state.personalized_video_url:
            st.markdown("##### ✨ Your Personalized Style Video is Ready!")
            
            # Display video information
            if st.session_state.personalized_video_job:
                job = st.session_state.personalized_video_job
                
                # Personalized video details
                with st.expander("📋 Your Personalized Video Details", expanded=True):
                    st.write(f"**Style Focus:** {style_focus_options.get(job.get('styleFocus', 'wardrobe'), 'Fashion & Wardrobe')}")
                    st.write(f"**Duration:** {job.get('duration', 6)} seconds")
                    st.write(f"**Method:** True Image-to-Video (shows YOU!)")
                    
                    if job.get('specificRecommendations'):
                        st.write(f"**Your Recommendations:** {', '.join(job['specificRecommendations'])}")
                    
                    if job.get('personalizedPrompt'):
                        st.write(f"**AI Prompt Used:**")
                        st.text_area("Personalization prompt:", job['personalizedPrompt'], height=100, key="personalized_prompt_display")
                    
                    st.write(f"**Generated:** {job.get('timestamp', 'N/A')}")
            
            # Video display
            st.markdown("**🎬 Watch Yourself in Recommended Styles:**")
            
            # Try to display video directly
            try:
                st.video(st.session_state.personalized_video_url)
                st.success("👤 This video shows YOU wearing the recommended styles!")
            except Exception as e:
                # Fallback to download link
                st.markdown(f"[🔗 **Download Your Personalized Style Video**]({st.session_state.personalized_video_url})")
                st.info("Click the link above to download and view your personalized style video.")
            
            # Action buttons
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("🔄 Generate New", key="generate_new_personalized"):
                    # Reset video generation state
                    st.session_state.personalized_video_job = None
                    st.session_state.personalized_video_in_progress = False
                    st.session_state.personalized_video_url = None
                    st.rerun()
            
            with col_b:
                st.markdown(f"[📥 Download]({st.session_state.personalized_video_url})")
            
            with col_c:
                if st.button("📋 Copy Link", key="copy_personalized_link"):
                    st.code(st.session_state.personalized_video_url)
                    st.success("Link copied to display!")
        
        elif st.session_state.personalized_video_in_progress:
            # Show progress
            st.markdown("##### 🎬 Creating Your Personalized Style Video...")
            
            if st.session_state.personalized_video_job:
                job = st.session_state.personalized_video_job
                
                # Progress information
                st.info(f"**Status:** {job.get('status', 'Unknown')}")
                st.info(f"**Job ID:** {job.get('jobId', 'N/A')[:8]}...")
                
                # Show what's being generated
                st.markdown("**🎯 Your Personalized Video:**")
                st.write(f"• **You will appear** wearing {style_focus_options.get(job.get('styleFocus', 'wardrobe'), 'recommended styles')}")
                st.write(f"• **Duration:** {job.get('duration', 6)} seconds")
                st.write(f"• **Method:** True Image-to-Video")
                
                if job.get('specificRecommendations'):
                    st.write(f"• **Specific Items:** {', '.join(job['specificRecommendations'])}")
                
                # Estimated time
                st.markdown("⏱️ **Estimated Time:** 2-3 minutes")
                
                # What makes this special
                st.success("🌟 **What makes this special**: You'll see YOUR face and body wearing the recommended styles - not a generic person!")
        
        else:
            # Instructions
            st.info("👈 Upload your photo to see yourself in recommended styles!")
            
            st.markdown("##### 🌟 True Personalized Videos:")
            st.markdown("""
            **🎯 Revolutionary Feature:**
            - Upload YOUR photo
            - See YOURSELF wearing recommended styles
            - Maintains your facial features and body type
            - Shows you in different outfits and settings
            
            **🎬 How it works:**
            1. **Upload your photo** - any clear image of yourself
            2. **Choose style focus** - wardrobe, lifestyle, etc.
            3. **Add specific recommendations** - optional items you want to see
            4. **AI generates video** showing YOU in those styles
            
            **✨ The Result:**
            A personalized video where you can see exactly how you'd look in the recommended styles!
            """)
            
            st.markdown("##### 💡 Tips for Best Results:")
            st.markdown("""
            - **Clear, well-lit photos** work best
            - **Face clearly visible** for better results
            - **Good quality images** produce better videos
            - **Try different style focuses** for variety
            """)
    
    # Footer for the tab
    st.markdown("---")
    st.markdown("*🎬 **BREAKTHROUGH**: True Personalized Style Videos powered by Nova Reel Image-to-Video*")
    st.markdown("**🚀 Revolutionary**: See YOURSELF wearing recommended styles - not generic models!")
