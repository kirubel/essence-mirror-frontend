import streamlit as st

# Configure Streamlit page - MUST BE FIRST
st.set_page_config(
    page_title="EssenceMirror - See Yourself in Recommended Styles!",
    page_icon="✨",
    layout="wide"
)

import boto3
import uuid
from datetime import datetime
import json
import time
import base64
import os
from io import BytesIO
from PIL import Image
import logging
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Feature flag for True Image-to-Video functionality
TRUE_IMAGE_VIDEO_ENABLED = True

# Initialize AWS clients with environment-based credentials for production
@st.cache_resource
def init_aws_clients():
    try:
        # Try to use environment variables first (production)
        session = boto3.Session()
        
        # Test if credentials are available
        sts_client = session.client('sts', region_name='us-east-1')
        identity = sts_client.get_caller_identity()
        logger.info(f"AWS credentials found - Account: {identity.get('Account', 'Unknown')}")
        
        return {
            's3': session.client('s3', region_name='us-east-1'),
            'bedrock_agent': session.client('bedrock-agent-runtime', region_name='us-east-1'),
            'lambda': session.client('lambda', region_name='us-east-1')
        }
    except Exception as e:
        logger.error(f"AWS credentials not available: {str(e)}")
        st.error("⚠️ AWS credentials not configured. Please set up AWS credentials in Streamlit Cloud secrets.")
        st.info("""
        **To fix this:**
        1. Go to your Streamlit Cloud app settings
        2. Add these secrets:
           - `AWS_ACCESS_KEY_ID`
           - `AWS_SECRET_ACCESS_KEY` 
           - `AWS_DEFAULT_REGION` (set to 'us-east-1')
        3. Redeploy the app
        """)
        # Return None clients to prevent further errors
        return {
            's3': None,
            'bedrock_agent': None,
            'lambda': None
        }

clients = init_aws_clients()

# Configuration
S3_BUCKET = "essencemirror-user-uploads"
AGENT_ID = "WWIUY28GRY"
AGENT_ALIAS_ID = "TSTALIASID"

def get_proper_content_type(uploaded_file):
    """Get the proper content type for the uploaded file"""
    # First try to get it from the uploaded file
    if hasattr(uploaded_file, 'type') and uploaded_file.type:
        return uploaded_file.type
    
    # Fallback to guessing from filename
    filename = uploaded_file.name.lower()
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        return 'image/jpeg'
    elif filename.endswith('.png'):
        return 'image/png'
    elif filename.endswith('.webp'):
        return 'image/webp'
    elif filename.endswith('.gif'):
        return 'image/gif'
    else:
        # Default to JPEG for unknown image types
        return 'image/jpeg'

def upload_image_to_s3(uploaded_file):
    """Upload image to S3 with proper content type handling"""
    if not clients['s3']:
        st.error("AWS S3 not available. Please configure AWS credentials.")
        return None
        
    try:
        # Generate unique filename with proper extension
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure we have the right file extension
        original_name = uploaded_file.name.lower()
        if original_name.endswith('.jpg') or original_name.endswith('.jpeg'):
            file_extension = 'jpg'
            content_type = 'image/jpeg'
        elif original_name.endswith('.png'):
            file_extension = 'png'
            content_type = 'image/png'
        elif original_name.endswith('.webp'):
            file_extension = 'webp'
            content_type = 'image/webp'
        else:
            # Default to JPEG
            file_extension = 'jpg'
            content_type = 'image/jpeg'
        
        s3_key = f"uploads/streamlit_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Reset file pointer to beginning
        uploaded_file.seek(0)
        
        # Upload to S3 with explicit content type
        clients['s3'].upload_fileobj(
            uploaded_file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'Metadata': {
                    'original-filename': uploaded_file.name,
                    'upload-timestamp': timestamp
                }
            }
        )
        
        logger.info(f"Uploaded {s3_key} with content type {content_type}")
        return s3_key
        
    except Exception as e:
        st.error(f"Error uploading image: {str(e)}")
        logger.error(f"Upload error: {str(e)}")
        return None

def invoke_bedrock_agent(message, session_id):
    """Invoke the Bedrock agent with a message"""
    if not clients['bedrock_agent']:
        st.error("AWS Bedrock not available. Please configure AWS credentials.")
        return None
        
    try:
        response = clients['bedrock_agent'].invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message
        )
        
        # Process the streaming response
        full_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')
        
        return full_response
    except Exception as e:
        st.error(f"Error invoking agent: {str(e)}")
        logger.error(f"Agent invocation error: {str(e)}")
        return None

def generate_recommendations_direct(session_id):
    """Generate recommendations using Lambda function directly"""
    if not clients['lambda']:
        st.error("AWS Lambda not available. Please configure AWS credentials.")
        return None
        
    try:
        # Call Lambda function directly for better control
        recommendations_event = {
            "messageVersion": "1.0",
            "sessionId": session_id,
            "actionGroup": "EssenceMirrorActions",
            "httpMethod": "POST",
            "apiPath": "/generateRecommendations",
            "requestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {
                                "name": "lifestyle_focus",
                                "value": "general"
                            }
                        ]
                    }
                }
            }
        }
        
        lambda_response = clients['lambda'].invoke(
            FunctionName='essenceMirror',
            Payload=json.dumps(recommendations_event)
        )
        
        response_payload = json.loads(lambda_response['Payload'].read())
        
        if 'response' in response_payload and 'responseBody' in response_payload['response']:
            response_body = response_payload['response']['responseBody']
            if 'application/json' in response_body:
                body_content = json.loads(response_body['application/json']['body'])
                
                if 'recommendations' in body_content:
                    return body_content['recommendations']
                elif 'error' in body_content:
                    st.error(f"Error generating recommendations: {body_content['error']}")
                    return None
        
        return None
        
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        logger.error(f"Recommendations error: {str(e)}")
        return None

def generate_style_collage(session_id, category="lifestyle"):
    """Generate a category-specific style collage using Nova Canvas"""
    if not clients['lambda']:
        st.error("AWS Lambda not available. Please configure AWS credentials.")
        return None
        
    try:
        # Call the Lambda function directly for Nova Canvas
        test_event = {
            "messageVersion": "1.0",
            "sessionId": session_id,
            "actionGroup": "EssenceMirrorActions",
            "httpMethod": "POST",
            "apiPath": "/generateStyleCollage",
            "requestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {
                                "name": "style_focus",
                                "value": category
                            },
                            {
                                "name": "color_preference",
                                "value": "personalized"
                            }
                        ]
                    }
                }
            }
        }
        
        lambda_response = clients['lambda'].invoke(
            FunctionName='essenceMirror',
            Payload=json.dumps(test_event)
        )
        
        response_payload = json.loads(lambda_response['Payload'].read())
        
        if 'response' in response_payload and 'responseBody' in response_payload['response']:
            response_body = response_payload['response']['responseBody']
            if 'application/json' in response_body:
                body_content = json.loads(response_body['application/json']['body'])
                
                # Return both URL, base64, and prompt for better display options
                result = {}
                if 'collage_url' in body_content:
                    result['url'] = body_content['collage_url']
                if 'collage_base64' in body_content:
                    result['base64'] = body_content['collage_base64']
                if 'prompt_used' in body_content:
                    result['prompt_used'] = body_content['prompt_used']
                
                if result:
                    return result
                elif 'error' in body_content:
                    st.error(f"Error generating collage: {body_content['error']}")
                    return None
        
        return None
        
    except Exception as e:
        st.error(f"Error generating style collage: {str(e)}")
        logger.error(f"Collage generation error: {str(e)}")
        return None

def display_recommendations(recommendations):
    """Display recommendations in a user-friendly format"""
    if not recommendations:
        st.warning("No recommendations available")
        return
    
    st.markdown("#### 🌟 Your Personalized Recommendations")
    
    # Create tabs for different categories if we have structured data
    if isinstance(recommendations, list) and len(recommendations) > 0:
        # Check if recommendations are structured
        if isinstance(recommendations[0], dict) and 'category' in recommendations[0]:
            # Group recommendations by category
            categories = {}
            for rec in recommendations:
                category = rec.get('category', 'General')
                if category not in categories:
                    categories[category] = []
                categories[category].append(rec)
            
            # Create tabs for each category
            if len(categories) > 1:
                tab_names = list(categories.keys())
                tabs = st.tabs([f"🎯 {cat}" for cat in tab_names])
                
                for i, (category, recs) in enumerate(categories.items()):
                    with tabs[i]:
                        for j, rec in enumerate(recs, 1):
                            with st.container():
                                st.markdown(f"**💡 Recommendation {j}:**")
                                st.write(rec.get('recommendation', 'N/A'))
                                if 'rationale' in rec and rec['rationale']:
                                    with st.expander("💭 Why this works for you"):
                                        st.write(rec.get('rationale', 'N/A'))
                                st.markdown("---")
            else:
                # Single category - display directly
                category_name = list(categories.keys())[0]
                recs = categories[category_name]
                for j, rec in enumerate(recs, 1):
                    with st.container():
                        st.markdown(f"**💡 {category_name} Recommendation {j}:**")
                        st.write(rec.get('recommendation', 'N/A'))
                        if 'rationale' in rec and rec['rationale']:
                            with st.expander("💭 Why this works for you"):
                                st.write(rec.get('rationale', 'N/A'))
                        st.markdown("---")
        else:
            # Simple list format
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"**{i}.** {rec}")
    else:
        # Text format
        st.write(recommendations)

def validate_image_file(uploaded_file):
    """Validate that the uploaded file is a proper image"""
    try:
        # Try to open with PIL to validate it's a real image
        image = Image.open(uploaded_file)
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Check image format
        if image.format not in ['JPEG', 'PNG', 'WEBP']:
            st.warning(f"Image format {image.format} detected. Converting to JPEG for better compatibility.")
        
        return True
    except Exception as e:
        st.error(f"Invalid image file: {str(e)}")
        return False

def main():
    # Import the component here to avoid early Streamlit calls
    try:
        from true_image_video_component import render_true_image_video_tab
    except ImportError as e:
        st.error(f"Error importing true image-to-video component: {str(e)}")
        st.info("Some features may not be available.")
        render_true_image_video_tab = None
    
    # Import Nova Sonic component
    try:
        from nova_sonic_component import render_nova_sonic_tab
        nova_sonic_available = True
    except ImportError as e:
        st.error(f"Error importing Nova Sonic component: {str(e)}")
        st.info("Voice conversation features may not be available.")
        render_nova_sonic_tab = None
        nova_sonic_available = False
    
    # Header
    st.title("✨ EssenceMirror")
    st.subheader("Discover Your Personal Style & Create Dynamic Content")
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'profile_data' not in st.session_state:
        st.session_state.profile_data = None
    if 'recommendations_generated' not in st.session_state:
        st.session_state.recommendations_generated = False
    if 'recommendations_data' not in st.session_state:
        st.session_state.recommendations_data = None
    if 'collage_data' not in st.session_state:
        st.session_state.collage_data = None
    if 'collage_category' not in st.session_state:
        st.session_state.collage_category = 'lifestyle'
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ✨ EssenceMirror Features:")
        st.markdown("1. 📸 **Style Analysis** - Upload & analyze your style")
        st.markdown("2. 🎨 **Visual Collages** - AI-generated mood boards")
        st.markdown("3. 🎬 **Style Videos** - Dynamic style content")
        st.markdown("---")
        st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        
        # Feature status
        st.markdown("---")
        st.markdown("### 🚀 Available Features:")
        st.markdown("✅ Style Analysis (Fixed MIME types)")
        st.markdown("✅ Visual Collages (Nova Canvas)")
        if TRUE_IMAGE_VIDEO_ENABLED:
            st.markdown("✅ **BREAKTHROUGH**: See Yourself in Styles!")
        else:
            st.markdown("🚧 Personalized Videos (Coming Soon)")
        
        # Tips
        st.markdown("---")
        st.markdown("### 💡 Tips:")
        st.markdown("• Use clear, well-lit photos")
        st.markdown("• Supported formats: JPG, PNG, WebP")
        st.markdown("• **NEW**: See YOURSELF in recommended styles")
        st.markdown("• Videos show your actual face and body")
        st.markdown("• Try different style recommendations")
        
        # Debug info
        st.markdown("---")
        st.markdown("### 🔧 System Status:")
        try:
            identity = clients['s3'].meta.client._client_config.__dict__.get('region_name', 'Unknown')
            st.markdown(f"• Region: {identity}")
            st.markdown("• Auth: ✅ Working")
        except:
            st.markdown("• Auth: ❌ Check credentials")
    
    # Create tabs for different features
    if TRUE_IMAGE_VIDEO_ENABLED and nova_sonic_available:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Style Analysis", 
            "🎨 Visual Collages", 
            "🎬 See Yourself in Styles",
            "🎙️ Voice Style Consultant"
        ])
    elif TRUE_IMAGE_VIDEO_ENABLED:
        tab1, tab2, tab3 = st.tabs([
            "📊 Style Analysis", 
            "🎨 Visual Collages", 
            "🎬 See Yourself in Styles"
        ])
    elif nova_sonic_available:
        tab1, tab2, tab3 = st.tabs([
            "📊 Style Analysis", 
            "🎨 Visual Collages", 
            "🎙️ Voice Style Consultant"
        ])
    else:
        tab1, tab2 = st.tabs([
            "📊 Style Analysis", 
            "🎨 Visual Collages"
        ])
    
    # Tab 1: Style Analysis
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📸 Upload Your Photo")
            
            uploaded_file = st.file_uploader(
                "Choose an image file",
                type=['png', 'jpg', 'jpeg', 'webp'],
                help="Upload a clear photo of yourself for style analysis. Supported formats: JPG, PNG, WebP",
                key="analysis_uploader"
            )
            
            if uploaded_file is not None:
                # Validate the image file
                if validate_image_file(uploaded_file):
                    # Display uploaded image
                    st.image(uploaded_file, caption="Your uploaded image", use_column_width=True)
                    
                    # Show file details
                    with st.expander("📋 File Details"):
                        st.write(f"**Filename:** {uploaded_file.name}")
                        st.write(f"**Size:** {uploaded_file.size:,} bytes")
                        st.write(f"**Type:** {get_proper_content_type(uploaded_file)}")
                    
                    # Upload and analyze button
                    if st.button("🔍 Analyze My Style", type="primary", key="analyze_btn"):
                        with st.spinner("Uploading image and analyzing your style..."):
                            # Upload to S3
                            s3_key = upload_image_to_s3(uploaded_file)
                            
                            if s3_key:
                                # Create S3 URL for agent
                                s3_url = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{s3_key}"
                                
                                # Invoke agent for analysis
                                analysis_message = f"I want to analyze {s3_url}"
                                analysis_response = invoke_bedrock_agent(
                                    analysis_message, 
                                    st.session_state.session_id
                                )
                                
                                if analysis_response:
                                    st.session_state.profile_data = analysis_response
                                    st.session_state.analysis_complete = True
                                    st.success("✅ Analysis complete!")
                                    st.rerun()
                                else:
                                    st.error("❌ Analysis failed. Please try again with a different image.")
        
        with col2:
            st.markdown("### 🎯 Your Style Profile")
            
            if st.session_state.analysis_complete and st.session_state.profile_data:
                # Generate recommendations button (prominent at top)
                if not st.session_state.recommendations_generated:
                    if st.button("✨ Get My Recommendations", type="primary", key="rec_btn"):
                        with st.spinner("Generating your personalized recommendations..."):
                            recommendations = generate_recommendations_direct(st.session_state.session_id)
                            
                            if recommendations:
                                st.session_state.recommendations_data = recommendations
                                st.session_state.recommendations_generated = True
                                st.success("🎉 Your personalized recommendations are ready!")
                                st.rerun()
                
                # Display recommendations prominently if available
                if st.session_state.recommendations_generated and st.session_state.recommendations_data:
                    display_recommendations(st.session_state.recommendations_data)
                    st.markdown("---")
                
                # Analysis results (moved below recommendations)
                with st.expander("📊 View Detailed Style Analysis", expanded=False):
                    st.markdown("#### Analysis Results:")
                    st.write(st.session_state.profile_data)
                    
            else:
                st.info("👆 Upload an image to get started with your style analysis!")
    
    # Tab 2: Visual Collages
    with tab2:
        if st.session_state.analysis_complete:
            st.markdown("### 🎨 Visual Style Collages")
            st.markdown("Generate beautiful mood boards focused on specific areas of your lifestyle!")
            
            # Category selection
            collage_categories = {
                "wardrobe": "👗 Wardrobe & Fashion",
                "interior": "🏠 Home & Interior Design", 
                "travel": "✈️ Travel & Experiences",
                "lifestyle": "🌟 Complete Lifestyle"
            }
            
            selected_category = st.selectbox(
                "Select collage focus:",
                options=list(collage_categories.keys()),
                format_func=lambda x: collage_categories[x],
                index=0,
                key="collage_selector"
            )
            
            # Style collage generation button
            if st.button(f"🎨 Generate {collage_categories[selected_category]} Collage", type="primary", key="collage_btn"):
                with st.spinner(f"Creating your personalized {collage_categories[selected_category].lower()} collage... This may take a few seconds."):
                    collage_result = generate_style_collage(st.session_state.session_id, selected_category)
                    
                    if collage_result:
                        st.session_state.collage_data = collage_result
                        st.session_state.collage_category = selected_category
                        st.success(f"🎉 Your {collage_categories[selected_category].lower()} collage is ready!")
                        st.rerun()
            
            # Display generated collage
            if hasattr(st.session_state, 'collage_data') and st.session_state.collage_data:
                category_name = collage_categories.get(st.session_state.get('collage_category', 'lifestyle'), 'Style')
                st.markdown(f"#### 🖼️ Your {category_name} Collage:")
                
                # Try to display the image using different methods
                collage_displayed = False
                
                # Method 1: Try base64 if available
                if 'base64' in st.session_state.collage_data:
                    try:
                        # Decode base64 image
                        image_data = base64.b64decode(st.session_state.collage_data['base64'])
                        
                        # Display using st.image with BytesIO
                        st.image(
                            BytesIO(image_data),
                            caption=f"Your AI-Generated {category_name} Mood Board", 
                            use_column_width=True
                        )
                        collage_displayed = True
                        
                        # Display the prompt used (for troubleshooting)
                        if 'prompt_used' in st.session_state.collage_data:
                            with st.expander("🔍 View Prompt Used"):
                                st.text_area("Prompt for Nova Canvas", 
                                            st.session_state.collage_data['prompt_used'], 
                                            height=200)
                        
                    except Exception as e:
                        st.warning(f"Could not display image from base64: {str(e)}")
                
                # Method 2: Try URL if base64 failed
                if not collage_displayed and 'url' in st.session_state.collage_data:
                    try:
                        st.image(
                            st.session_state.collage_data['url'], 
                            caption=f"Your AI-Generated {category_name} Mood Board", 
                            use_column_width=True
                        )
                        collage_displayed = True
                        
                    except Exception as e:
                        st.warning(f"Could not display image from URL: {str(e)}")
                
                # Method 3: Fallback to link
                if not collage_displayed:
                    st.error("Could not display image directly. Here's the link:")
                    if 'url' in st.session_state.collage_data:
                        st.markdown(f"[🔗 View Your {category_name} Collage]({st.session_state.collage_data['url']})")
                
                # Additional options
                if collage_displayed:
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        if st.button("🔄 Generate New", key="new_collage_btn"):
                            with st.spinner(f"Creating a new {collage_categories[st.session_state.collage_category].lower()} collage..."):
                                new_collage = generate_style_collage(st.session_state.session_id, st.session_state.collage_category)
                                if new_collage:
                                    st.session_state.collage_data = new_collage
                                    st.success("🎉 New collage generated!")
                                    st.rerun()
                    
                    with col_b:
                        if 'url' in st.session_state.collage_data:
                            st.markdown(f"[🔗 Full Size]({st.session_state.collage_data['url']})")
                    
                    with col_c:
                        # Category switch button
                        if st.button("🎯 Change Focus", key="change_focus_btn"):
                            # Clear current collage to show category selector
                            if hasattr(st.session_state, 'collage_data'):
                                del st.session_state.collage_data
                            st.rerun()
                
        else:
            st.info("Complete your style analysis first to generate visual collages!")
    
    # Tab 3: True Image-to-Video (if enabled)
    if TRUE_IMAGE_VIDEO_ENABLED:
        with tab3:
            if render_true_image_video_tab:
                render_true_image_video_tab(st.session_state.session_id, st.session_state.analysis_complete)
            else:
                st.error("True Image-to-Video component not available")
                st.info("Please check the component installation and try again.")
    
    # Tab 4: Nova Sonic Voice Consultant (if enabled and available)
    if nova_sonic_available:
        # Determine which tab to use based on available features
        if TRUE_IMAGE_VIDEO_ENABLED:
            nova_sonic_tab = tab4
        else:
            nova_sonic_tab = tab3
        
        with nova_sonic_tab:
            if render_nova_sonic_tab:
                render_nova_sonic_tab(
                    session_id=st.session_state.session_id,
                    analysis_complete=st.session_state.analysis_complete,
                    style_analysis_data=st.session_state.get('analysis_result', None)
                )
            else:
                st.error("Nova Sonic Voice Consultant not available")
                st.info("Please check the Nova Sonic component installation and try again.")
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Amazon Bedrock, Nova Pro AI, Nova Canvas, Nova Reel, and Nova Sonic*")
    st.markdown("**🚀 BREAKTHROUGH**: Complete AI Style Experience - Visual Analysis + True Image Videos + Voice Conversations!")

if __name__ == "__main__":
    main()
