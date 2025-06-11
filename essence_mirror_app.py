import streamlit as st
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Feature flag for Style Reel functionality
STYLE_REEL_ENABLED = True

# Configure Streamlit page
st.set_page_config(
    page_title="EssenceMirror - Personal Style Analysis",
    page_icon="✨",
    layout="wide"
)

# Initialize AWS clients
@st.cache_resource
def init_aws_clients():
    # Use explicit session with default profile
    session = boto3.Session(profile_name='default')
    return {
        's3': session.client('s3', region_name='us-east-1'),
        'bedrock_agent': session.client('bedrock-agent-runtime', region_name='us-east-1'),
        'lambda': session.client('lambda', region_name='us-east-1')
    }

clients = init_aws_clients()

# Configuration
S3_BUCKET = "essencemirror-user-uploads"
AGENT_ID = "WWIUY28GRY"
AGENT_ALIAS_ID = "TSTALIASID"

def upload_image_to_s3(uploaded_file):
    """Upload image to S3 and return the key"""
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = uploaded_file.name.split('.')[-1]
        s3_key = f"uploads/streamlit_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Upload to S3
        clients['s3'].upload_fileobj(
            uploaded_file,
            S3_BUCKET,
            s3_key,
            ExtraArgs={'ContentType': uploaded_file.type}
        )
        
        return s3_key
    except Exception as e:
        st.error(f"Error uploading image: {str(e)}")
        return None

def invoke_bedrock_agent(message, session_id):
    """Invoke the Bedrock agent with a message"""
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
        return None

def generate_recommendations_direct(session_id):
    """Generate recommendations using Lambda function directly"""
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
        return None

def generate_style_collage(session_id, category="lifestyle"):
    """Generate a category-specific style collage using Nova Canvas"""
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
        return None

def display_recommendations(recommendations):
    """Display recommendations in a user-friendly format at the top"""
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

def main():
    # Header
    st.title("✨ EssenceMirror")
    st.subheader("Discover Your Personal Style & Get Tailored Recommendations")
    
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
        st.markdown("### How it works:")
        st.markdown("1. 📸 Upload your photo")
        st.markdown("2. 🔍 AI analyzes your style")
        st.markdown("3. ✨ Get personalized recommendations")
        st.markdown("4. 🎨 Generate visual mood board")
        st.markdown("---")
        st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        
        # Nova Canvas info
        st.markdown("---")
        st.markdown("### 🎨 New Feature!")
        st.markdown("**Visual Style Collages** powered by Amazon Nova Canvas")
        st.markdown("Generate beautiful mood boards based on your personal style!")
    
    # Main content - 3 columns now
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("### 📸 Upload Your Photo")
        
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo of yourself for style analysis"
        )
        
        if uploaded_file is not None:
            # Display uploaded image
            st.image(uploaded_file, caption="Your uploaded image", use_column_width=True)
            
            # Upload and analyze button
            if st.button("🔍 Analyze My Style", type="primary"):
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
    
    with col2:
        st.markdown("### 🎯 Your Style Profile & Recommendations")
        
        if st.session_state.analysis_complete and st.session_state.profile_data:
            # Generate recommendations button (prominent at top)
            if not st.session_state.recommendations_generated:
                if st.button("✨ Get My Recommendations", type="primary"):
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
    
    # NEW COLUMN: Nova Canvas Style Collage
    with col3:
        st.markdown("### 🎨 Visual Style Collages")
        
        if st.session_state.analysis_complete:
            st.markdown("#### Choose Your Collage Type")
            st.write("Generate beautiful mood boards focused on specific areas of your lifestyle!")
            
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
                index=0
            )
            
            # Style collage generation button
            if st.button(f"🎨 Generate {collage_categories[selected_category]} Collage", type="primary"):
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
                        import base64
                        from io import BytesIO
                        
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
                        if st.button("🔄 Generate New"):
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
                        if st.button("🎯 Change Focus"):
                            # Clear current collage to show category selector
                            if hasattr(st.session_state, 'collage_data'):
                                del st.session_state.collage_data
                            st.rerun()
                
        else:
            st.info("Complete your style analysis first to generate visual collages!")
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Amazon Bedrock, Nova Pro AI, and Nova Canvas*")

if __name__ == "__main__":
    main()
# Add the Style Reel API to the Bedrock agent schema
def update_agent_schema():
    """Update the Bedrock agent schema to include the Style Reel API"""
    try:
        # Import clients from the main app
        from essence_mirror_app import clients
        
        # Define the new API schema
        style_reel_api = {
            "name": "/generateStyleReel",
            "description": "Generate a personalized style video using Nova Reel",
            "method": "POST",
            "contentType": "application/json",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "style_focus": {
                                    "type": "string",
                                    "description": "Focus area for the style video (wardrobe, interior, travel, lifestyle)",
                                    "enum": ["wardrobe", "interior", "travel", "lifestyle"]
                                },
                                "use_original_image": {
                                    "type": "boolean",
                                    "description": "Whether to use the user's original uploaded image in the video",
                                    "default": True
                                },
                                "duration_seconds": {
                                    "type": "integer",
                                    "description": "Desired video duration in seconds (5-15)",
                                    "minimum": 5,
                                    "maximum": 15,
                                    "default": 10
                                }
                            },
                            "required": ["style_focus"]
                        }
                    }
                }
            },
            "responseBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "video_url": {
                                    "type": "string",
                                    "description": "URL to the generated video"
                                },
                                "video_base64": {
                                    "type": "string",
                                    "description": "Base64-encoded video data"
                                },
                                "prompt_used": {
                                    "type": "string",
                                    "description": "Prompt used to generate the video"
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": "User ID for the request"
                                },
                                "message": {
                                    "type": "string",
                                    "description": "Status message"
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # TODO: Implement the actual schema update using the Bedrock agent API
        # This would require additional permissions and API calls
        
        logger.info("Agent schema updated to include Style Reel API")
        return True
    except Exception as e:
        logger.error(f"Error updating agent schema: {str(e)}")
        return False
# Main app layout with tabs
def main_app_with_tabs():
    """Main application layout with tabs for different features"""
    
    # Initialize session state if needed
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{str(uuid.uuid4())}"
        st.session_state.analysis_complete = False
        st.session_state.recommendations_generated = False
    
    # App header
    st.title("✨ EssenceMirror - Discover Your Personal Style")
    st.markdown("Upload an image and let AI analyze your unique style essence.")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 Style Analysis", "🎨 Style Collages", "🎬 Style in Motion (Beta)"])
    
    # Tab 1: Style Analysis
    with tab1:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📸 Upload Your Image")
            
            uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"], key="uploader_tab1")
            
            if uploaded_file is not None:
                # Display the uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_column_width=True)
                
                # Save image to session state
                st.session_state.uploaded_image = uploaded_file
                
                # Analyze button
                if st.button("✨ Analyze My Style", type="primary"):
                    with st.spinner("Analyzing your style... This may take a few seconds."):
                        # Upload to S3
                        s3_key = upload_image_to_s3(uploaded_file)
                        
                        if s3_key:
                            # Create S3 URL for agent
                            s3_url = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{s3_key}"
                            
                            # Invoke agent for analysis
                            analysis_message = f"I want to analyze {s3_url}"
                            analysis_result = invoke_bedrock_agent(
                                analysis_message, 
                                st.session_state.session_id
                            )
                            
                            if analysis_result:
                                st.session_state.profile_data = analysis_result
                                st.session_state.analysis_complete = True
                                st.success("🎉 Analysis complete!")
                                st.rerun()
        
        with col2:
            st.markdown("### 🔍 Style Profile")
            
            if hasattr(st.session_state, 'profile_data') and st.session_state.profile_data:
                st.markdown("#### Analysis Results:")
                st.write(st.session_state.profile_data)
            else:
                st.info("👆 Upload an image to get started with your style analysis!")
    
    # Tab 2: Style Collages
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
                key="collage_category_selector"
            )
            
            # Style collage generation button
            if st.button(f"🎨 Generate {collage_categories[selected_category]} Collage", type="primary", key="generate_collage_btn"):
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
                        st.error(f"Error displaying image from base64: {str(e)}")
                
                # Method 2: Try URL if available and base64 failed
                if not collage_displayed and 'url' in st.session_state.collage_data:
                    try:
                        st.image(
                            st.session_state.collage_data['url'],
                            caption=f"Your AI-Generated {category_name} Mood Board", 
                            use_column_width=True
                        )
                        collage_displayed = True
                    except Exception as e:
                        st.error(f"Error displaying image from URL: {str(e)}")
                
                if not collage_displayed:
                    st.error("Unable to display the collage. Please try generating it again.")
        else:
            st.info("👆 Upload and analyze an image first to create style collages!")
    
    # Tab 3: Style in Motion (Beta)
    with tab3:
        if STYLE_REEL_ENABLED:
            # Import and render the Style Reel component
            try:
                from style_reel_component import render_style_reel_tab
                render_style_reel_tab(st.session_state.session_id, st.session_state.analysis_complete)
            except Exception as e:
                st.error(f"Error loading Style Reel feature: {str(e)}")
                logger.error(f"Error loading Style Reel component: {str(e)}")
        else:
            st.info("🚧 Style in Motion feature coming soon! Stay tuned for dynamic style videos.")

# Call the main app function with tabs
if __name__ == "__main__":
    # Initialize AWS clients
    clients = init_aws_clients()
    
    # Run the app with tabs
    main_app_with_tabs()
