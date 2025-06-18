import streamlit as st
import boto3
import uuid
from datetime import datetime
import json
import time
import sys
import os
import tempfile
from PIL import Image

# Add infrastructure path for Nova Reel
sys.path.append('/Users/kirubelaklilu/Documents/EssenceMirror/essence-mirror-infrastructure')

try:
    from nova_reel_generator import NovaReelGenerator
    from image_inspired_generator import create_image_inspired_prompt, analyze_image_basic
    NOVA_REEL_AVAILABLE = True
except ImportError as e:
    st.warning(f"Nova Reel functionality not available: {str(e)}")
    NOVA_REEL_AVAILABLE = False

# Configure Streamlit page
st.set_page_config(
    page_title="EssenceMirror - Personal Style Analysis",
    page_icon="✨",
    layout="wide"
)

# Initialize AWS clients
@st.cache_resource
def init_aws_clients():
    return {
        's3': boto3.client('s3', region_name='us-east-1'),
        'bedrock_agent': boto3.client('bedrock-agent-runtime', region_name='us-east-1'),
        'lambda': boto3.client('lambda', region_name='us-east-1')
    }

clients = init_aws_clients()

# Configuration
S3_BUCKET = "essencemirror-user-uploads"
AGENT_ID = "WWIUY28GRY"
AGENT_ALIAS_ID = "TSTALIASID"

def generate_image_specific_analysis(image_hash):
    """Generate image-specific analysis based on image hash"""
    import hashlib
    
    # Generate varied profiles based on image hash for testing
    # Create more diverse profiles including youth and different contexts
    profiles = [
        {
            "archetype": "Young Athletic Enthusiast",
            "visual_style": ["Sporty", "Casual", "Active"],
            "energetic_essence": ["Energetic", "Playful", "Confident"],
            "age_group": "youth",
            "gender": "unspecified",
            "style_category": "athletic",
            "detailed_analysis": """
## Visual Aesthetic Analysis
This young individual demonstrates a natural affinity for athletic and active wear. The style choices reflect someone who prioritizes comfort, movement, and functionality while maintaining a youthful, energetic appearance.

## Style Elements Observed
- **Athletic Focus**: Clear preference for sportswear and performance fabrics
- **Comfort Priority**: Values ease of movement and breathable materials
- **Casual Approach**: Relaxed, age-appropriate styling choices
- **Activity-Ready**: Clothing choices support active lifestyle and play
- **Youthful Energy**: Style reflects vibrant, energetic personality

## Energetic Essence
Projects youthful confidence and enthusiasm for physical activity. There's a natural, unforced energy that suggests someone who is comfortable being active and values practical, fun clothing choices.

## Personal Archetype: Young Athletic Enthusiast
Someone who loves sports, outdoor activities, and staying active. Values comfort and functionality while expressing their energetic, playful personality through their clothing choices.

## Recommendations Focus
- Age-appropriate athletic wear
- Comfortable, durable pieces for active play
- Bright, fun colors that reflect youthful energy
- Practical items that support an active lifestyle
            """.strip()
        },
        {
            "archetype": "Creative Professional",
            "visual_style": ["Artistic", "Expressive", "Contemporary"],
            "energetic_essence": ["Innovative", "Authentic", "Confident"],
            "age_group": "adult", 
            "gender": "unspecified",
            "style_category": "creative",
            "detailed_analysis": """
## Visual Aesthetic Analysis
This individual showcases a creative approach to personal style with artistic flair and contemporary sensibilities. The aesthetic suggests someone who uses fashion as a form of self-expression and creative outlet.

## Style Elements Observed
- **Artistic Expression**: Uses clothing to communicate personality and creativity
- **Color Experimentation**: Comfortable with bold colors and interesting combinations
- **Texture Play**: Appreciates varied textures and unique fabric choices
- **Statement Pieces**: Incorporates distinctive items that spark conversation
- **Individual Approach**: Creates unique looks rather than following trends blindly

## Energetic Essence
Radiates creativity and authenticity. There's an innovative spirit that approaches style as an art form. Confident in making bold choices and expressing individuality.

## Personal Archetype: Creative Professional
Someone who balances artistic expression with professional requirements, using style as a creative outlet while maintaining workplace appropriateness.
            """.strip()
        },
        {
            "archetype": "Classic Minimalist", 
            "visual_style": ["Clean", "Timeless", "Refined"],
            "energetic_essence": ["Sophisticated", "Intentional", "Elegant"],
            "age_group": "adult",
            "gender": "unspecified", 
            "style_category": "minimalist",
            "detailed_analysis": """
## Visual Aesthetic Analysis
This individual embodies a minimalist philosophy with emphasis on quality, simplicity, and timeless appeal. The aesthetic suggests someone who values craftsmanship and intentional choices over quantity.

## Style Elements Observed
- **Quality Over Quantity**: Invests in well-made, lasting pieces
- **Neutral Palette**: Sophisticated use of neutrals and classic colors
- **Clean Lines**: Appreciates simple, elegant silhouettes
- **Timeless Appeal**: Chooses pieces that transcend seasonal trends
- **Intentional Curation**: Every item serves a purpose and fits the overall aesthetic

## Energetic Essence
Projects quiet confidence and sophistication. There's an elegance that comes from restraint and careful curation. Values substance over flash.

## Personal Archetype: Classic Minimalist
Someone who has developed a refined aesthetic based on quality, simplicity, and timeless appeal. Approaches style with intention and sophistication.
            """.strip()
        },
        {
            "archetype": "Casual Comfort Seeker",
            "visual_style": ["Relaxed", "Comfortable", "Practical"],
            "energetic_essence": ["Easygoing", "Authentic", "Approachable"],
            "age_group": "adult",
            "gender": "unspecified",
            "style_category": "casual",
            "detailed_analysis": """
## Visual Aesthetic Analysis
This individual prioritizes comfort and practicality in their style choices. The approach to fashion is relaxed and authentic, focusing on pieces that feel good and work well for daily life.

## Style Elements Observed
- **Comfort First**: Prioritizes how clothing feels over strict fashion rules
- **Practical Choices**: Selects items that work for multiple activities
- **Relaxed Fit**: Prefers clothing that allows for easy movement
- **Versatile Pieces**: Chooses items that can be mixed and matched easily
- **Authentic Style**: Stays true to personal preferences over trends

## Energetic Essence
Projects an easygoing, approachable energy. There's an authenticity that comes from being comfortable in one's own skin and making practical choices.

## Personal Archetype: Casual Comfort Seeker
Someone who values comfort and practicality while maintaining a put-together appearance. Approaches style with a relaxed, authentic mindset.
            """.strip()
        }
    ]
    
    # Select profile based on image hash for variety
    profile_index = int(image_hash, 16) % len(profiles)
    analysis_response = profiles[profile_index]
    
    # Add image-specific details
    analysis_response["image_id"] = image_hash
    analysis_response["upload_timestamp"] = datetime.now().isoformat()
    
    return analysis_response

def parse_analysis_text(analysis_text):
    """Parse analysis text to extract structured profile data"""
    try:
        # Convert text to structured profile
        profile = {
            "archetype": "Unknown",
            "visual_style": [],
            "energetic_essence": [],
            "age_group": "adult",  # Default
            "style_category": "general",  # Default
            "gender": "unspecified",  # Add gender detection
            "detailed_analysis": analysis_text  # Store the full analysis
        }
        
        text_lower = analysis_text.lower()
        
        # Detect gender
        male_indicators = ["boy", "man", "male", "masculine", "him", "his", "he", "gentleman", "guy"]
        female_indicators = ["girl", "woman", "female", "feminine", "her", "hers", "she", "lady", "gal", "pregnant", "pregnancy"]
        
        male_count = sum(1 for word in male_indicators if word in text_lower)
        female_count = sum(1 for word in female_indicators if word in text_lower)
        
        if male_count > female_count:
            profile["gender"] = "male"
        elif female_count > male_count:
            profile["gender"] = "female"
        else:
            profile["gender"] = "unspecified"
        
        # Detect age group
        youth_indicators = ["child", "kid", "young", "youth", "teen", "adolescent", "boy", "girl", "student", "school"]
        adult_indicators = ["adult", "professional", "mature", "woman", "man", "pregnant", "mother", "father"]
        
        youth_count = sum(1 for word in youth_indicators if word in text_lower)
        adult_count = sum(1 for word in adult_indicators if word in text_lower)
        
        if youth_count > adult_count:
            profile["age_group"] = "youth"
        else:
            profile["age_group"] = "adult"
        
        # Detect style category
        if any(word in text_lower for word in ["athletic", "sport", "active", "fitness", "gym", "soccer", "football", "basketball", "running"]):
            profile["style_category"] = "athletic"
        elif any(word in text_lower for word in ["casual", "relaxed", "everyday", "comfortable"]):
            profile["style_category"] = "casual"
        elif any(word in text_lower for word in ["formal", "professional", "business", "work", "office"]):
            profile["style_category"] = "professional"
        elif any(word in text_lower for word in ["creative", "artistic", "expressive", "unique", "individual"]):
            profile["style_category"] = "creative"
        
        # Extract archetype based on content with gender and age consideration
        if profile["age_group"] == "youth" and profile["style_category"] == "athletic":
            if profile["gender"] == "male":
                profile["archetype"] = "Young Athletic Boy"
                profile["visual_style"] = ["Sporty", "Active", "Comfortable", "Youthful"]
            elif profile["gender"] == "female":
                profile["archetype"] = "Young Athletic Girl"
                profile["visual_style"] = ["Sporty", "Active", "Comfortable", "Youthful"]
            else:
                profile["archetype"] = "Young Athlete"
                profile["visual_style"] = ["Sporty", "Active", "Comfortable"]
            profile["energetic_essence"] = ["Energetic", "Playful", "Active", "Confident"]
            
        elif profile["gender"] == "female" and any(word in text_lower for word in ["pregnant", "pregnancy", "expecting", "maternity"]):
            profile["archetype"] = "Expecting Mother"
            profile["visual_style"] = ["Comfortable", "Adaptable", "Feminine", "Practical"]
            profile["energetic_essence"] = ["Nurturing", "Glowing", "Anticipatory", "Graceful"]
            profile["style_category"] = "maternity"
            
        elif profile["style_category"] == "athletic":
            if profile["gender"] == "male":
                profile["archetype"] = "Athletic Professional (Male)"
                profile["visual_style"] = ["Performance-focused", "Modern", "Functional", "Masculine"]
            elif profile["gender"] == "female":
                profile["archetype"] = "Athletic Professional (Female)"
                profile["visual_style"] = ["Performance-focused", "Modern", "Functional", "Feminine"]
            else:
                profile["archetype"] = "Athletic Professional"
                profile["visual_style"] = ["Performance-focused", "Modern", "Functional"]
            profile["energetic_essence"] = ["Dynamic", "Health-conscious", "Active"]
            
        elif profile["style_category"] == "creative":
            profile["archetype"] = "Creative Individual"
            profile["visual_style"] = ["Artistic", "Expressive", "Contemporary"]
            profile["energetic_essence"] = ["Innovative", "Authentic", "Confident"]
            
        else:
            # Default based on gender and age
            if profile["age_group"] == "youth":
                profile["archetype"] = "Young Individual"
                profile["visual_style"] = ["Youthful", "Casual", "Comfortable"]
                profile["energetic_essence"] = ["Energetic", "Playful", "Authentic"]
            elif profile["gender"] == "male":
                profile["archetype"] = "Modern Man"
                profile["visual_style"] = ["Contemporary", "Versatile", "Masculine"]
                profile["energetic_essence"] = ["Confident", "Authentic", "Grounded"]
            elif profile["gender"] == "female":
                profile["archetype"] = "Modern Woman"
                profile["visual_style"] = ["Contemporary", "Versatile", "Feminine"]
                profile["energetic_essence"] = ["Confident", "Authentic", "Elegant"]
            else:
                profile["archetype"] = "Modern Individual"
                profile["visual_style"] = ["Contemporary", "Versatile"]
                profile["energetic_essence"] = ["Confident", "Authentic"]
        
        return profile
        
    except Exception as e:
        st.error(f"Error parsing analysis: {str(e)}")
        return {
            "archetype": "Style Enthusiast",
            "visual_style": ["Contemporary"],
            "energetic_essence": ["Confident"],
            "gender": "unspecified",
            "age_group": "adult",
            "detailed_analysis": analysis_text
        }

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

def generate_recommendations_direct(session_id, profile_data=None):
    """Generate recommendations using Lambda function directly with profile data"""
    try:
        # Use profile data if available, otherwise use default
        if profile_data:
            profile_value = profile_data
        else:
            # Default profile for testing
            profile_value = {
                "archetype": "Modern Professional",
                "visual_style": ["Contemporary", "Refined"],
                "energetic_essence": ["Confident", "Sophisticated"]
            }
        
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
                                "name": "profile",
                                "value": profile_value
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
            
            # Handle direct recommendations in responseBody
            if 'recommendations' in response_body:
                return response_body['recommendations']
            
            # Handle JSON string in responseBody
            elif 'application/json' in response_body:
                body_content = json.loads(response_body['application/json']['body'])
                
                if 'recommendations' in body_content:
                    return body_content['recommendations']
                elif 'error' in body_content:
                    st.error(f"Error generating recommendations: {body_content['error']}")
                    return None
        
        # Handle error cases
        if 'errorMessage' in response_payload:
            st.error(f"Lambda error: {response_payload['errorMessage']}")
            return None
        
        return None
        
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return None

def generate_style_collage(session_id, category="lifestyle", profile_data=None, recommendations_data=None):
    """Generate a category-specific style collage using Nova Canvas with gender awareness"""
    try:
        # Extract gender information from profile
        gender_context = ""
        if profile_data and isinstance(profile_data, dict):
            gender = profile_data.get('gender', 'unspecified')
            age_group = profile_data.get('age_group', 'adult')
            
            if gender == 'male':
                if age_group == 'youth':
                    gender_context = "for boys, masculine youth style"
                else:
                    gender_context = "for men, masculine style"
            elif gender == 'female':
                if age_group == 'youth':
                    gender_context = "for girls, feminine youth style"
                else:
                    gender_context = "for women, feminine style"
            else:
                gender_context = "gender-neutral style"
        
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
                            },
                            {
                                "name": "gender_context",
                                "value": gender_context
                            },
                            {
                                "name": "profile_data",
                                "value": json.dumps(profile_data) if profile_data else "{}"
                            },
                            {
                                "name": "recommendations_data",
                                "value": json.dumps(recommendations_data) if recommendations_data else "{}"
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
            
            # Handle direct responseBody format (current Lambda response format)
            if isinstance(response_body, dict):
                body_content = response_body
            elif 'application/json' in response_body:
                body_content = json.loads(response_body['application/json']['body'])
            else:
                body_content = response_body
                
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

def save_uploaded_file_temporarily(uploaded_file):
    """Save uploaded file to a temporary location for processing"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error saving temporary file: {str(e)}")
        return None

def generate_style_video(image_path, user_prompt=None, style_focus="lifestyle", duration=6):
    """Generate a style video using Nova Reel"""
    if not NOVA_REEL_AVAILABLE:
        st.error("Nova Reel functionality is not available")
        return None
    
    try:
        # Initialize Nova Reel generator
        generator = NovaReelGenerator()
        
        # Create image-inspired prompt
        if not user_prompt:
            user_prompt = f"Create a stylish {style_focus} video showcasing modern fashion and aesthetic appeal"
        
        # Generate video
        result = generator.generate_video_from_user_input(
            user_input=user_prompt,
            user_id="streamlit_user",
            duration_seconds=duration
        )
        
        if result and result.get('status') == 'completed':
            return result.get('video_url')
        else:
            st.error(f"Video generation failed: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        st.error(f"Error generating style video: {str(e)}")
        return None

def clean_text(text):
    """Clean markdown formatting artifacts from text"""
    if not text:
        return text
    
    # Remove various markdown formatting
    cleaned = str(text)
    cleaned = cleaned.replace('**', '')  # Bold markers
    cleaned = cleaned.replace('*', '')   # Italic markers
    cleaned = cleaned.replace('_', '')   # Underscore formatting
    cleaned = cleaned.replace('`', '')   # Code formatting
    cleaned = cleaned.replace('#', '')   # Header markers
    cleaned = cleaned.replace('---', '') # Horizontal rules
    cleaned = cleaned.replace('- ', '')  # List markers
    cleaned = cleaned.replace('+ ', '')  # List markers
    cleaned = cleaned.replace('> ', '')  # Quote markers
    
    # Clean up extra whitespace
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def display_recommendations(recommendations):
    """Display enhanced recommendations in a user-friendly format"""
    if not recommendations:
        st.warning("No recommendations available")
        return
    
    st.markdown("#### 🌟 Your Personalized Fashion Recommendations")
    
    # Check if we have enhanced recommendations with specific structure
    if isinstance(recommendations, list) and len(recommendations) > 0:
        first_rec = recommendations[0]
        
        # Enhanced recommendations format
        if isinstance(first_rec, dict) and ('budget_option' in first_rec or 'category' in first_rec):
            for i, rec in enumerate(recommendations, 1):
                with st.expander(f"🎯 {rec.get('category', f'Recommendation {i}')}", expanded=True):
                    
                    # Budget Option
                    if 'budget_option' in rec and rec['budget_option']:
                        budget = rec['budget_option']
                        st.markdown("##### 💰 Budget Option")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            # Clean up brand and product names
                            brand = clean_text(budget.get('brand', 'N/A'))
                            product = clean_text(budget.get('product', 'N/A'))
                            price = clean_text(budget.get('price', 'N/A'))
                            where = clean_text(budget.get('where', 'N/A'))
                            
                            st.markdown(f"**{brand} - {product}**")
                            st.write(f"💵 {price}")
                            st.write(f"🛒 {where}")
                        with col2:
                            if budget.get('why'):
                                why_text = clean_text(budget['why'])
                                st.info(why_text)
                    
                    # Mid-Range Option
                    if 'mid_range_option' in rec and rec['mid_range_option']:
                        mid = rec['mid_range_option']
                        st.markdown("##### 🎯 Mid-Range Option")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            # Clean up formatting
                            brand = clean_text(mid.get('brand', 'N/A'))
                            product = clean_text(mid.get('product', 'N/A'))
                            price = clean_text(mid.get('price', 'N/A'))
                            where = clean_text(mid.get('where', 'N/A'))
                            
                            st.markdown(f"**{brand} - {product}**")
                            st.write(f"💵 {price}")
                            st.write(f"🛒 {where}")
                        with col2:
                            if mid.get('why'):
                                why_text = clean_text(mid['why'])
                                st.info(why_text)
                    
                    # Premium Option
                    if 'premium_option' in rec and rec['premium_option']:
                        premium = rec['premium_option']
                        st.markdown("##### ✨ Premium Option")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            # Clean up formatting
                            brand = clean_text(premium.get('brand', 'N/A'))
                            product = clean_text(premium.get('product', 'N/A'))
                            price = clean_text(premium.get('price', 'N/A'))
                            where = clean_text(premium.get('where', 'N/A'))
                            
                            st.markdown(f"**{brand} - {product}**")
                            st.write(f"💵 {price}")
                            st.write(f"🛒 {where}")
                        with col2:
                            if premium.get('why'):
                                why_text = clean_text(premium['why'])
                                st.info(why_text)
                    
                    # Styling Tips and Additional Info
                    if rec.get('styling_tips') or rec.get('seasonal_note') or rec.get('priority_level'):
                        st.markdown("---")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if rec.get('styling_tips'):
                                st.markdown("**👗 Styling Tips:**")
                                styling_text = clean_text(rec['styling_tips'])
                                st.write(styling_text)
                        
                        with col2:
                            if rec.get('seasonal_note'):
                                st.markdown("**🌤️ Seasonal Note:**")
                                seasonal_text = clean_text(rec['seasonal_note'])
                                st.write(seasonal_text)
                        
                        with col3:
                            if rec.get('priority_level'):
                                priority = clean_text(rec['priority_level'])
                                if 'High' in priority:
                                    st.markdown("**🔥 Priority:** High")
                                elif 'Medium' in priority:
                                    st.markdown("**⚡ Priority:** Medium")
                                else:
                                    st.markdown(f"**📌 Priority:** {priority}")
                
                st.markdown("---")
        
        # Legacy format support
        elif isinstance(first_rec, dict) and 'category' in first_rec and 'recommendation' in first_rec:
            for i, rec in enumerate(recommendations, 1):
                with st.container():
                    st.markdown(f"**💡 Recommendation {i}:**")
                    recommendation_text = clean_text(rec.get('recommendation', 'N/A'))
                    st.write(recommendation_text)
                    if 'rationale' in rec and rec['rationale']:
                        with st.expander("💭 Why this works for you"):
                            rationale_text = clean_text(rec.get('rationale', 'N/A'))
                            st.write(rationale_text)
                    st.markdown("---")
        
        # Simple list format
        else:
            for i, rec in enumerate(recommendations, 1):
                cleaned_rec = clean_text(str(rec))
                st.markdown(f"**{i}.** {cleaned_rec}")
    else:
        # Text format
        cleaned_recommendations = clean_text(str(recommendations))
        st.write(cleaned_recommendations)

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
    if 'video_generated' not in st.session_state:
        st.session_state.video_generated = False
    if 'video_url' not in st.session_state:
        st.session_state.video_url = None
    if 'current_image_hash' not in st.session_state:
        st.session_state.current_image_hash = None
    if 's3_key' not in st.session_state:
        st.session_state.s3_key = None
    
    # Sidebar
    with st.sidebar:
        st.markdown("### How it works:")
        st.markdown("1. 📸 Upload your photo")
        st.markdown("2. 🔍 AI analyzes your style")
        st.markdown("3. ✨ Get personalized recommendations")
        st.markdown("4. 🎨 Generate visual mood board")
        if NOVA_REEL_AVAILABLE:
            st.markdown("5. 🎬 Create style video")
        st.markdown("---")
        st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        
        # Features info
        st.markdown("---")
        st.markdown("### 🎨 Features")
        st.markdown("**Enhanced Recommendations** with specific brands and prices")
        st.markdown("**Visual Style Collages** powered by Amazon Nova Canvas")
        if NOVA_REEL_AVAILABLE:
            st.markdown("**Style Videos** powered by Amazon Nova Reel")
    
    # Main content - 4 columns if Nova Reel available, 3 otherwise
    if NOVA_REEL_AVAILABLE:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("### 📸 Upload Your Photo")
        
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo of yourself for style analysis"
        )
        
        if uploaded_file is not None:
            # Generate image hash immediately when file is uploaded
            import hashlib
            file_bytes = uploaded_file.getvalue()
            image_hash = hashlib.md5(file_bytes).hexdigest()[:8]
            
            # Check if this is a new image (different hash)
            if st.session_state.current_image_hash != image_hash:
                # New image uploaded - reset all analysis data
                st.session_state.current_image_hash = image_hash
                st.session_state.analysis_complete = False
                st.session_state.profile_data = None
                st.session_state.recommendations_generated = False
                st.session_state.recommendations_data = None
                st.session_state.collage_data = None
                st.session_state.video_generated = False
                st.session_state.video_url = None
                st.info("🔄 New image detected - ready for fresh analysis!")
            
            # Display uploaded image
            st.image(uploaded_file, caption="Your uploaded image", use_column_width=True)
            
            # Upload and analyze button
            if st.button("🔍 Analyze My Style", type="primary"):
                with st.spinner("Uploading image and analyzing your style..."):
                    # Upload to S3
                    s3_key = upload_image_to_s3(uploaded_file)
                    
                    if s3_key:
                        st.session_state.s3_key = s3_key
                        st.success("✅ Image uploaded successfully!")
                        
                        # Call Lambda function for REAL image analysis
                        analysis_event = {
                            "messageVersion": "1.0",
                            "sessionId": st.session_state.session_id,
                            "actionGroup": "EssenceMirrorActions",
                            "httpMethod": "POST",
                            "apiPath": "/analyzeImage",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "properties": [
                                            {
                                                "name": "bucket_name",
                                                "value": S3_BUCKET
                                            },
                                            {
                                                "name": "object_key", 
                                                "value": s3_key
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                        
                        lambda_response = clients['lambda'].invoke(
                            FunctionName='essenceMirror',
                            Payload=json.dumps(analysis_event)
                        )
                        
                        response_payload = json.loads(lambda_response['Payload'].read())
                        
                        # Extract the actual analysis from Lambda response
                        analysis_response = None
                        if 'response' in response_payload and 'responseBody' in response_payload['response']:
                            response_body = response_payload['response']['responseBody']
                            
                            # Check for error first
                            if 'error' in response_body:
                                st.error(f"❌ Analysis failed: {response_body['error']}")
                                st.info("💡 Please try uploading the image again.")
                                return
                            
                            # Extract profile data
                            if 'profile' in response_body:
                                analysis_response = response_body['profile']
                                
                                # If profile is empty or has "Unknown" archetype, try parsing the analysis text
                                if (not analysis_response or 
                                    analysis_response.get('archetype') == 'Unknown' or 
                                    not analysis_response.get('visual_style')):
                                    
                                    if 'analysis' in response_body:
                                        # Parse the full analysis text to extract better profile
                                        analysis_text = response_body['analysis']
                                        if isinstance(analysis_text, dict) and 'output' in analysis_text:
                                            # Extract text from Nova Pro response structure
                                            if 'message' in analysis_text['output'] and 'content' in analysis_text['output']['message']:
                                                content = analysis_text['output']['message']['content']
                                                if content and len(content) > 0 and 'text' in content[0]:
                                                    text_content = content[0]['text']
                                                    parsed_profile = parse_analysis_text(text_content)
                                                    if parsed_profile and parsed_profile.get('archetype') != 'Unknown':
                                                        analysis_response = parsed_profile
                        
                        # If Lambda analysis failed or returned empty profile, show error
                        if not analysis_response or analysis_response.get('archetype') == 'Unknown':
                            st.error("❌ Could not analyze this image. Please try with a clearer photo showing a person.")
                            st.info("💡 Make sure the image shows a person clearly and try again.")
                        else:
                            st.session_state.profile_data = analysis_response
                            st.session_state.analysis_complete = True
                            st.success("🎉 Style analysis complete!")
                            st.rerun()
                    else:
                        st.error("❌ Failed to upload image. Please try again.")
                    
                    if s3_key:
                        # Create S3 URL for agent
                        s3_url = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{s3_key}"
                        
                        # Invoke agent for analysis - use direct Lambda call instead
                        analysis_event = {
                            "messageVersion": "1.0",
                            "sessionId": st.session_state.session_id,
                            "actionGroup": "EssenceMirrorActions",
                            "httpMethod": "POST",
                            "apiPath": "/analyzeImage",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "properties": [
                                            {
                                                "name": "bucket_name",
                                                "value": S3_BUCKET
                                            },
                                            {
                                                "name": "object_key", 
                                                "value": s3_key
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                        
                        lambda_response = clients['lambda'].invoke(
                            FunctionName='essenceMirror',
                            Payload=json.dumps(analysis_event)
                        )
                        
                        response_payload = json.loads(lambda_response['Payload'].read())
                        
                        # Generate image-specific analysis using stored hash
                        if st.session_state.current_image_hash:
                            analysis_response = generate_image_specific_analysis(st.session_state.current_image_hash)
                        else:
                            # Fallback: generate a default hash if somehow missing
                            import time
                            fallback_hash = str(int(time.time()))[-8:]
                            analysis_response = generate_image_specific_analysis(fallback_hash)
                        
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
                if st.button("✨ Get My Recommendations", type="primary", use_container_width=True):
                    with st.spinner("Generating your personalized recommendations..."):
                        # Debug: Show what profile we're sending
                        st.write("🔍 **Debug - Profile being sent:**")
                        st.json(st.session_state.profile_data)
                        
                        # Pass the profile data to the recommendation function
                        recommendations = generate_recommendations_direct(
                            st.session_state.session_id, 
                            st.session_state.profile_data
                        )
                        
                        # Debug: Show what we got back
                        st.write("🔍 **Debug - Recommendations received:**")
                        st.write(f"Type: {type(recommendations)}")
                        st.write(f"Length: {len(recommendations) if recommendations else 'None'}")
                        if recommendations:
                            st.write("First recommendation structure:")
                            st.json(recommendations[0] if len(recommendations) > 0 else {})
                        
                        if recommendations:
                            st.session_state.recommendations_data = recommendations
                            st.session_state.recommendations_generated = True
                            st.success("🎉 Your personalized recommendations are ready!")
                            st.rerun()
                        else:
                            st.error("❌ No recommendations were generated. Please try again.")
                            st.write("This might be a Lambda function issue. Check the debug output above.")
            
            # Display recommendations if generated
            if st.session_state.recommendations_generated and st.session_state.recommendations_data:
                display_recommendations(st.session_state.recommendations_data)
            
            # Display profile data in a user-friendly format
            if st.session_state.profile_data:
                st.markdown("### 📋 Your Style Profile")
                
                # Try to parse and display nicely
                if isinstance(st.session_state.profile_data, dict):
                    # Structured profile data
                    if 'archetype' in st.session_state.profile_data:
                        st.markdown(f"**🎭 Archetype:** {st.session_state.profile_data['archetype']}")
                    
                    if 'gender' in st.session_state.profile_data and st.session_state.profile_data['gender'] != 'unspecified':
                        gender_icon = "👨" if st.session_state.profile_data['gender'] == 'male' else "👩"
                        st.markdown(f"**{gender_icon} Gender:** {st.session_state.profile_data['gender'].title()}")
                    
                    if 'age_group' in st.session_state.profile_data:
                        age_icon = "🧒" if st.session_state.profile_data['age_group'] == 'youth' else "👤"
                        st.markdown(f"**{age_icon} Age Group:** {st.session_state.profile_data['age_group'].title()}")
                    
                    if 'visual_style' in st.session_state.profile_data:
                        st.markdown("**👗 Visual Style:**")
                        if isinstance(st.session_state.profile_data['visual_style'], list):
                            for style in st.session_state.profile_data['visual_style']:
                                st.write(f"• {style}")
                        else:
                            st.write(st.session_state.profile_data['visual_style'])
                    
                    if 'energetic_essence' in st.session_state.profile_data:
                        st.markdown("**✨ Energetic Essence:**")
                        if isinstance(st.session_state.profile_data['energetic_essence'], list):
                            for essence in st.session_state.profile_data['energetic_essence']:
                                st.write(f"• {essence}")
                        else:
                            st.write(st.session_state.profile_data['energetic_essence'])
                    
                    # Show detailed analysis if available
                    if 'detailed_analysis' in st.session_state.profile_data:
                        with st.expander("📖 Detailed Style Analysis", expanded=False):
                            st.markdown(st.session_state.profile_data['detailed_analysis'])
                    
                    # Show raw data in separate section
                    if st.checkbox("🔍 Show Raw Analysis Data"):
                        st.json(st.session_state.profile_data)
                else:
                    # Text-based analysis - try to format nicely
                    analysis_text = str(st.session_state.profile_data)
                    
                    # Extract key information
                    if "archetype" in analysis_text.lower():
                        st.markdown("**🎭 Style Analysis:**")
                        st.write(analysis_text)
                    else:
                        st.write(analysis_text)
        else:
            st.info("👆 Upload and analyze your photo first to get personalized recommendations")
    
    with col3:
        st.markdown("### 🎨 Visual Style Collage")
        
        if st.session_state.analysis_complete:
            # Debug info and test functionality
            debug_enabled = st.checkbox("🔍 Debug Info", key="debug_collage")
            
            if debug_enabled:
                st.write("**Session State Keys:**", list(st.session_state.keys()))
                collage_data = st.session_state.get('collage_data')
                if collage_data is not None:
                    st.write("**Collage Data Keys:**", list(collage_data.keys()))
                    st.write("**Collage Data Preview:**", {k: str(v)[:100] + "..." if len(str(v)) > 100 else str(v) for k, v in collage_data.items()})
                else:
                    st.write("**Collage Data:**", "None")
                
                recommendations_data = st.session_state.get('recommendations_data')
                st.write("**Has Recommendations:**", recommendations_data is not None)
                if recommendations_data:
                    st.write("**Recommendations Preview:**", str(recommendations_data)[:200] + "..." if len(str(recommendations_data)) > 200 else str(recommendations_data))
            
            # Category selection with enhanced descriptions
            collage_options = {
                "fashion": "🎽 Fashion Lookbook - Showcase your recommended items and brands",
                "lifestyle": "🌟 Lifestyle Vision - Your aspirational daily life aesthetic", 
                "color_palette": "🎨 Color Palette - Perfect color coordination guide",
                "interior": "🏠 Interior Aesthetic - Your ideal home environment",
                "mood": "✨ Artistic Mood - Creative interpretation of your style essence"
            }
            
            collage_category = st.selectbox(
                "Choose collage style:",
                list(collage_options.keys()),
                format_func=lambda x: collage_options[x],
                index=0,
                key="collage_category_select"
            )
            
            # Generate collage button
            if st.button("🎨 Generate Style Collage", use_container_width=True):
                with st.spinner(f"Creating your {collage_category} style collage..."):
                    try:
                        collage_result = generate_style_collage(
                            st.session_state.session_id, 
                            collage_category,
                            st.session_state.profile_data,
                            st.session_state.get('recommendations_data', None)
                        )
                        
                        if collage_result:
                            st.session_state.collage_data = collage_result
                            st.success("🎨 Your style collage is ready!")
                            
                            # Display immediately
                            if 'base64' in collage_result:
                                import base64
                                image_data = base64.b64decode(collage_result['base64'])
                                st.image(image_data, caption="Your Style Collage", use_column_width=True)
                            
                            if 'prompt_used' in collage_result:
                                with st.expander("🎯 Collage Inspiration"):
                                    st.write(collage_result['prompt_used'])
                        else:
                            st.error("Failed to generate collage. Please try again.")
                    except Exception as e:
                        st.error(f"Error generating collage: {str(e)}")
            
            # Test button for debugging (only show if debug is enabled)
            if debug_enabled:
                if st.button("🧪 Test Collage Generation", use_container_width=True):
                    with st.spinner("Testing collage generation..."):
                        try:
                            test_result = generate_style_collage(
                                "test-session-ui",
                                "fashion",
                                {"gender": "female", "age_group": "adult"},
                                {"recommendations": [{"brand": "Test Brand", "product": "Test Product"}]}
                            )
                            if test_result:
                                st.success("✅ Test collage generated successfully!")
                                if 'base64' in test_result:
                                    import base64
                                    image_data = base64.b64decode(test_result['base64'])
                                    st.image(image_data, caption="Test Collage", use_column_width=True)
                            else:
                                st.error("❌ Test collage generation failed")
                        except Exception as e:
                            st.error(f"❌ Test error: {str(e)}")
            
            # Display persistent collage
            collage_data = st.session_state.get('collage_data')
            if collage_data is not None:
                st.write("**Stored Collage:**")
                try:
                    if 'base64' in collage_data:
                        import base64
                        image_data = base64.b64decode(collage_data['base64'])
                        st.image(image_data, caption="Your Stored Style Collage", use_column_width=True)
                    
                    if st.button("🗑️ Clear Stored Collage", use_container_width=True):
                        st.session_state.collage_data = None
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error displaying stored collage: {str(e)}")
                    st.session_state.collage_data = None
        else:
            st.info("👆 Complete your style analysis first to generate visual collages")
    
    # Nova Reel column (if available)
    if NOVA_REEL_AVAILABLE:
        with col4:
            st.markdown("### 🎬 Style Video")
            
            if st.session_state.analysis_complete and uploaded_file is not None:
                # Video generation options
                video_style = st.selectbox(
                    "Video style:",
                    ["lifestyle", "fashion", "professional", "casual", "artistic"],
                    index=0
                )
                
                video_duration = st.slider("Duration (seconds):", 3, 10, 6)
                
                # Generate video button
                if st.button("🎬 Create Style Video", use_container_width=True):
                    with st.spinner(f"Creating your {video_style} style video... This may take a few minutes."):
                        # Save uploaded file temporarily
                        temp_path = save_uploaded_file_temporarily(uploaded_file)
                        
                        if temp_path:
                            try:
                                video_url = generate_style_video(
                                    temp_path, 
                                    f"Create a stylish {video_style} video",
                                    video_style,
                                    video_duration
                                )
                                
                                if video_url:
                                    st.session_state.video_url = video_url
                                    st.session_state.video_generated = True
                                    st.success("🎬 Your style video is ready!")
                                    st.rerun()
                            finally:
                                # Clean up temporary file
                                if os.path.exists(temp_path):
                                    os.unlink(temp_path)
                
                # Display video if generated
                if st.session_state.video_generated and st.session_state.video_url:
                    st.video(st.session_state.video_url)
                    st.success("🎬 Your personalized style video!")
            else:
                st.info("👆 Upload and analyze your photo first to create style videos")

if __name__ == "__main__":
    main()
