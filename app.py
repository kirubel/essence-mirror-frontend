import streamlit as st
import boto3
import uuid
from datetime import datetime
import json
import time
import os

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
        'bedrock_agent': boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    }

clients = init_aws_clients()

# Configuration - Use environment variables for production
S3_BUCKET = os.getenv("S3_BUCKET", "essencemirror-user-uploads")
AGENT_ID = os.getenv("AGENT_ID", "WWIUY28GRY")
AGENT_ALIAS_ID = os.getenv("AGENT_ALIAS_ID", "TSTALIASID")

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
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'recommendations_generated' not in st.session_state:
        st.session_state.recommendations_generated = False
    
    # Sidebar
    with st.sidebar:
        st.markdown("### How it works:")
        st.markdown("1. 📸 Upload your photo")
        st.markdown("2. 🔍 AI analyzes your style")
        st.markdown("3. ✨ Get personalized recommendations")
        st.markdown("4. 💬 Chat with your style advisor")
        st.markdown("5. 🔄 Update your profile anytime")
        st.markdown("---")
        st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        
        # Reset session button
        if st.button("🔄 Start New Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Create tabs for different features
    tab1, tab2, tab3, tab4 = st.tabs(["📸 Image Analysis", "🎯 Profile & Recommendations", "💬 Chat with Agent", "⚙️ Profile Settings"])
    
    with tab1:
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
                            st.session_state.chat_history.append({
                                "type": "analysis",
                                "message": analysis_message,
                                "response": analysis_response,
                                "timestamp": datetime.now()
                            })
                            st.success("✅ Analysis complete! Check the Profile & Recommendations tab.")
                            st.rerun()
    
    with tab2:
        st.markdown("### 🎯 Your Style Profile & Recommendations")
        
        if st.session_state.analysis_complete and st.session_state.profile_data:
            # Display analysis results
            st.markdown("#### 📋 Your Style Analysis:")
            st.write(st.session_state.profile_data)
            
            # Generate recommendations button
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("✨ Get My Recommendations", type="primary"):
                    with st.spinner("Generating your personalized recommendations..."):
                        recommendations_response = invoke_bedrock_agent(
                            "Generate recommendations", 
                            st.session_state.session_id
                        )
                        
                        if recommendations_response:
                            st.session_state.recommendations_data = recommendations_response
                            st.session_state.recommendations_generated = True
                            st.session_state.chat_history.append({
                                "type": "recommendations",
                                "message": "Generate recommendations",
                                "response": recommendations_response,
                                "timestamp": datetime.now()
                            })
                            st.balloons()
                            st.success("🎉 Your personalized recommendations are ready!")
                            st.rerun()
            
            with col2:
                if st.button("🔄 Update My Profile"):
                    st.info("💡 Use the Profile Settings tab or Chat tab to update your profile!")
            
            # Display recommendations if generated
            if st.session_state.recommendations_generated and 'recommendations_data' in st.session_state:
                st.markdown("#### 🌟 Your Personalized Recommendations:")
                st.write(st.session_state.recommendations_data)
                
                # Quick action buttons
                st.markdown("#### 🚀 Quick Actions:")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🎨 Focus on Wardrobe"):
                        with st.spinner("Getting wardrobe-focused recommendations..."):
                            wardrobe_response = invoke_bedrock_agent(
                                "Give me more detailed wardrobe recommendations", 
                                st.session_state.session_id
                            )
                            if wardrobe_response:
                                st.write("**Wardrobe Focus:**")
                                st.write(wardrobe_response)
                
                with col2:
                    if st.button("🏠 Focus on Interior"):
                        with st.spinner("Getting interior design recommendations..."):
                            interior_response = invoke_bedrock_agent(
                                "Give me more detailed interior design recommendations", 
                                st.session_state.session_id
                            )
                            if interior_response:
                                st.write("**Interior Focus:**")
                                st.write(interior_response)
                
                with col3:
                    if st.button("✈️ Focus on Travel"):
                        with st.spinner("Getting travel recommendations..."):
                            travel_response = invoke_bedrock_agent(
                                "Give me more detailed travel recommendations", 
                                st.session_state.session_id
                            )
                            if travel_response:
                                st.write("**Travel Focus:**")
                                st.write(travel_response)
        else:
            st.info("👆 Upload and analyze an image first to see your profile and get recommendations!")
    
    with tab3:
        st.markdown("### 💬 Chat with Your Style Advisor")
        
        if st.session_state.analysis_complete:
            # Display chat history
            if st.session_state.chat_history:
                st.markdown("#### 📜 Conversation History:")
                for i, chat in enumerate(st.session_state.chat_history):
                    with st.expander(f"💬 {chat['type'].title()} - {chat['timestamp'].strftime('%H:%M:%S')}"):
                        st.write(f"**You:** {chat['message']}")
                        st.write(f"**EssenceMirror:** {chat['response']}")
            
            # Chat input
            st.markdown("#### 💭 Ask me anything about your style:")
            
            # Predefined quick questions
            st.markdown("**Quick Questions:**")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("❓ What colors suit me best?"):
                    user_message = "What colors suit me best based on my analysis?"
                    with st.spinner("Getting color recommendations..."):
                        response = invoke_bedrock_agent(user_message, st.session_state.session_id)
                        if response:
                            st.session_state.chat_history.append({
                                "type": "chat",
                                "message": user_message,
                                "response": response,
                                "timestamp": datetime.now()
                            })
                            st.write(f"**EssenceMirror:** {response}")
                
                if st.button("❓ How can I improve my style?"):
                    user_message = "How can I improve my personal style?"
                    with st.spinner("Getting style improvement tips..."):
                        response = invoke_bedrock_agent(user_message, st.session_state.session_id)
                        if response:
                            st.session_state.chat_history.append({
                                "type": "chat",
                                "message": user_message,
                                "response": response,
                                "timestamp": datetime.now()
                            })
                            st.write(f"**EssenceMirror:** {response}")
            
            with col2:
                if st.button("❓ What's my style archetype?"):
                    user_message = "Tell me more about my style archetype and what it means"
                    with st.spinner("Explaining your archetype..."):
                        response = invoke_bedrock_agent(user_message, st.session_state.session_id)
                        if response:
                            st.session_state.chat_history.append({
                                "type": "chat",
                                "message": user_message,
                                "response": response,
                                "timestamp": datetime.now()
                            })
                            st.write(f"**EssenceMirror:** {response}")
                
                if st.button("❓ Budget-friendly options?"):
                    user_message = "Can you give me budget-friendly recommendations?"
                    with st.spinner("Finding budget options..."):
                        response = invoke_bedrock_agent(user_message, st.session_state.session_id)
                        if response:
                            st.session_state.chat_history.append({
                                "type": "chat",
                                "message": user_message,
                                "response": response,
                                "timestamp": datetime.now()
                            })
                            st.write(f"**EssenceMirror:** {response}")
            
            # Custom message input
            user_input = st.text_input("💬 Type your question:", placeholder="e.g., What accessories would work well with my style?")
            
            if st.button("Send Message", type="primary") and user_input:
                with st.spinner("Getting response..."):
                    response = invoke_bedrock_agent(user_input, st.session_state.session_id)
                    if response:
                        st.session_state.chat_history.append({
                            "type": "chat",
                            "message": user_input,
                            "response": response,
                            "timestamp": datetime.now()
                        })
                        st.write(f"**You:** {user_input}")
                        st.write(f"**EssenceMirror:** {response}")
                        st.rerun()
        else:
            st.info("👆 Complete your image analysis first to start chatting with your style advisor!")
    
    with tab4:
        st.markdown("### ⚙️ Profile Settings & Updates")
        
        if st.session_state.analysis_complete:
            st.markdown("#### 🔄 Update Your Profile")
            st.info("You can update specific aspects of your profile or provide additional context.")
            
            # Profile update options
            update_type = st.selectbox(
                "What would you like to update?",
                ["Select an option...", "Style Preferences", "Lifestyle Information", "Budget Constraints", "Specific Goals", "Custom Update"]
            )
            
            if update_type != "Select an option...":
                if update_type == "Style Preferences":
                    st.markdown("**Update your style preferences:**")
                    style_pref = st.text_area("Describe your style preferences:", placeholder="e.g., I prefer minimalist designs, love vintage pieces, or want to look more professional...")
                    
                    if st.button("Update Style Preferences") and style_pref:
                        update_message = f"Please update my profile with these style preferences: {style_pref}"
                        with st.spinner("Updating your style preferences..."):
                            response = invoke_bedrock_agent(update_message, st.session_state.session_id)
                            if response:
                                st.success("✅ Style preferences updated!")
                                st.write(response)
                
                elif update_type == "Lifestyle Information":
                    st.markdown("**Update your lifestyle information:**")
                    lifestyle_info = st.text_area("Describe your lifestyle:", placeholder="e.g., I work from home, attend many social events, am very active outdoors...")
                    
                    if st.button("Update Lifestyle Info") and lifestyle_info:
                        update_message = f"Please update my profile with this lifestyle information: {lifestyle_info}"
                        with st.spinner("Updating your lifestyle information..."):
                            response = invoke_bedrock_agent(update_message, st.session_state.session_id)
                            if response:
                                st.success("✅ Lifestyle information updated!")
                                st.write(response)
                
                elif update_type == "Budget Constraints":
                    st.markdown("**Set your budget preferences:**")
                    budget_range = st.selectbox("Select your budget range:", 
                                              ["Under $50", "$50-100", "$100-300", "$300-500", "$500-1000", "$1000+", "Custom"])
                    
                    if budget_range == "Custom":
                        custom_budget = st.text_input("Enter your custom budget range:")
                        budget_range = custom_budget if custom_budget else budget_range
                    
                    if st.button("Update Budget Preferences"):
                        update_message = f"Please update my profile with this budget range: {budget_range}"
                        with st.spinner("Updating your budget preferences..."):
                            response = invoke_bedrock_agent(update_message, st.session_state.session_id)
                            if response:
                                st.success("✅ Budget preferences updated!")
                                st.write(response)
                
                elif update_type == "Specific Goals":
                    st.markdown("**Set your style goals:**")
                    goals = st.text_area("What are your style goals?", placeholder="e.g., Look more professional for work, develop a signature style, prepare for a special event...")
                    
                    if st.button("Update Style Goals") and goals:
                        update_message = f"Please update my profile with these style goals: {goals}"
                        with st.spinner("Updating your style goals..."):
                            response = invoke_bedrock_agent(update_message, st.session_state.session_id)
                            if response:
                                st.success("✅ Style goals updated!")
                                st.write(response)
                
                elif update_type == "Custom Update":
                    st.markdown("**Custom profile update:**")
                    custom_update = st.text_area("What would you like to update or add to your profile?", placeholder="Describe any changes or additional information...")
                    
                    if st.button("Apply Custom Update") and custom_update:
                        update_message = f"Please update my profile: {custom_update}"
                        with st.spinner("Applying your custom update..."):
                            response = invoke_bedrock_agent(update_message, st.session_state.session_id)
                            if response:
                                st.success("✅ Profile updated!")
                                st.write(response)
            
            # Profile confirmation
            st.markdown("---")
            st.markdown("#### ✅ Profile Management")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 View Current Profile"):
                    with st.spinner("Retrieving your current profile..."):
                        response = invoke_bedrock_agent("Show me my current profile summary", st.session_state.session_id)
                        if response:
                            st.write("**Your Current Profile:**")
                            st.write(response)
            
            with col2:
                if st.button("✅ Confirm Profile"):
                    with st.spinner("Confirming your profile..."):
                        response = invoke_bedrock_agent("Please confirm my profile", st.session_state.session_id)
                        if response:
                            st.success("✅ Profile confirmed!")
                            st.write(response)
        else:
            st.info("👆 Complete your image analysis first to access profile settings!")
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Amazon Bedrock and Nova Pro AI*")

if __name__ == "__main__":
    main()
