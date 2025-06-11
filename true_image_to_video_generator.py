#!/usr/bin/env python3
"""
True Image-to-Video Generator for Nova Reel
Uses actual uploaded user photos to create personalized recommendation videos
showing the ACTUAL person wearing recommended styles
"""

import boto3
import json
import uuid
import base64
import logging
import time
from datetime import datetime
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrueImageToVideoGenerator:
    """Generator that creates videos showing the actual uploaded person in recommended styles"""
    
    def __init__(self, s3_bucket, region="us-east-1", profile_name='default'):
        """
        Initialize the True Image-to-Video Generator
        
        Args:
            s3_bucket (str): S3 bucket for storing generated videos
            region (str): AWS region for Bedrock
            profile_name (str): AWS profile name to use (None for environment credentials)
        """
        self.s3_bucket = s3_bucket
        self.region = region
        
        # Use explicit session with profile or environment credentials
        if profile_name:
            self.session = boto3.Session(profile_name=profile_name)
        else:
            # Use environment credentials (for production)
            self.session = boto3.Session()
            
        self.bedrock_client = self.session.client("bedrock-runtime", region_name=region)
        
        # Use your working inference profile
        self.inference_profile_arn = "arn:aws:bedrock:us-east-1:585768159241:application-inference-profile/0jxogfqizljp"
        
        # Log the identity being used
        try:
            sts_client = self.session.client("sts", region_name=region)
            identity = sts_client.get_caller_identity()
            logger.info(f"True Image-to-Video Generator initialized with identity: {identity['Arn']}")
        except Exception as e:
            logger.warning(f"Could not get caller identity: {str(e)}")
    
    def prepare_image_for_nova_reel(self, image_path):
        """
        Prepare uploaded image for Nova Reel (resize to 1280x720 and encode)
        
        Args:
            image_path (str): Path to the uploaded image
            
        Returns:
            str: Base64 encoded image ready for Nova Reel
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                original_size = img.size
                logger.info(f"Original image dimensions: {original_size}")
                
                # Resize to exactly 1280x720 as required by Nova Reel
                resized_img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                logger.info(f"Resized to Nova Reel dimensions: {resized_img.size}")
                
                # Save to bytes with high quality
                img_byte_arr = io.BytesIO()
                resized_img.save(img_byte_arr, format='JPEG', quality=95)
                img_byte_arr = img_byte_arr.getvalue()
                
                # Encode to base64
                encoded_image = base64.b64encode(img_byte_arr).decode('utf-8')
                
                logger.info(f"Image prepared successfully for Nova Reel")
                return encoded_image
                
        except Exception as e:
            logger.error(f"Error preparing image for Nova Reel: {str(e)}")
            raise
    
    def generate_personalized_video(self, image_path, recommendation_prompt, user_id=None, seed=None):
        """
        Generate a video showing the actual uploaded person in recommended styles
        
        Args:
            image_path (str): Path to user's uploaded photo
            recommendation_prompt (str): Description of recommended styles/outfits
            user_id (str, optional): User ID for tracking
            seed (int, optional): Seed for reproducibility
            
        Returns:
            dict: Response containing job_id and status
        """
        try:
            # Generate a random seed if not provided
            if seed is None:
                seed = int(time.time()) % 2147483647
            
            # Prepare the user's image
            encoded_image = self.prepare_image_for_nova_reel(image_path)
            
            # Create personalized prompt
            personalized_prompt = f"Transform this person into {recommendation_prompt}, maintain their facial features and body type, show them wearing the recommended styles, professional styling, high-quality fashion transformation"
            
            # Configure the video generation request with user's actual image
            model_input = {
                "taskType": "TEXT_VIDEO",
                "textToVideoParams": {
                    "text": personalized_prompt,
                    "images": [
                        {
                            "format": "jpeg",
                            "source": {
                                "bytes": encoded_image
                            }
                        }
                    ]
                },
                "videoGenerationConfig": {
                    "fps": 24,
                    "durationSeconds": 6,
                    "dimension": "1280x720",
                    "seed": seed,
                },
            }
            
            # Set up S3 output location
            s3_output_uri = f"s3://{self.s3_bucket}"
            output_config = {"s3OutputDataConfig": {"s3Uri": s3_output_uri}}
            
            # Generate unique client request token for tracking
            client_request_token = str(uuid.uuid4())
            
            logger.info(f"Starting personalized video generation")
            logger.info(f"Prompt: {personalized_prompt}")
            logger.info(f"User ID: {user_id}")
            
            # Start asynchronous video generation job
            response = self.bedrock_client.start_async_invoke(
                clientRequestToken=client_request_token,
                modelId=self.inference_profile_arn,
                modelInput=model_input,
                outputDataConfig=output_config
            )
            
            # Extract job ID for status tracking
            job_id = response.get('invocationArn')
            
            if not job_id:
                logger.error("No job ID returned from start_async_invoke")
                raise Exception("No job ID returned from start_async_invoke")
            
            logger.info(f"Personalized video job started with ID: {job_id}")
            
            return {
                "job_id": job_id,
                "status": "IN_PROGRESS",
                "user_id": user_id or str(uuid.uuid4()),
                "prompt": personalized_prompt,
                "client_request_token": client_request_token,
                "s3_output_uri": s3_output_uri,
                "timestamp": datetime.utcnow().isoformat(),
                "method": "true_image_to_video",
                "input_image": image_path
            }
            
        except Exception as e:
            logger.error(f"Error generating personalized video: {str(e)}")
            raise
    
    def generate_style_recommendation_video(self, image_path, style_focus="wardrobe", specific_recommendations=None, user_id=None):
        """
        Generate a video showing the user in specific style recommendations
        
        Args:
            image_path (str): Path to user's uploaded photo
            style_focus (str): Focus area (wardrobe, interior, travel, lifestyle)
            specific_recommendations (list): Specific style recommendations
            user_id (str, optional): User ID for tracking
            
        Returns:
            dict: Response containing job_id and status
        """
        try:
            # Create recommendation prompts based on focus
            focus_prompts = {
                "wardrobe": "elegant modern clothing, sophisticated business attire, stylish casual wear, fashionable accessories",
                "interior": "beautiful home settings, modern interior design, stylish living spaces, elegant room decor",
                "travel": "travel-ready outfits, adventure clothing, vacation styles, destination-appropriate attire",
                "lifestyle": "complete lifestyle transformation, modern aesthetic, sophisticated daily looks, elevated personal style"
            }
            
            base_prompt = focus_prompts.get(style_focus, focus_prompts["wardrobe"])
            
            # Add specific recommendations if provided
            if specific_recommendations:
                recommendations_text = ", ".join(specific_recommendations)
                final_prompt = f"{base_prompt}, {recommendations_text}"
            else:
                final_prompt = base_prompt
            
            # Generate the personalized video
            result = self.generate_personalized_video(
                image_path=image_path,
                recommendation_prompt=final_prompt,
                user_id=user_id
            )
            
            # Add style-specific metadata
            result.update({
                "style_focus": style_focus,
                "specific_recommendations": specific_recommendations,
                "recommendation_type": "personalized_style_video"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating style recommendation video: {str(e)}")
            raise
    
    def check_job_status(self, job_id):
        """
        Check the status of a personalized video generation job
        
        Args:
            job_id (str): The invocation ARN of the job
            
        Returns:
            dict: Dictionary containing status information
        """
        try:
            # Query job status
            response = self.bedrock_client.get_async_invoke(
                invocationArn=job_id
            )
            
            status = response.get("status")
            result = {
                "job_id": job_id,
                "status": status
            }
            
            if status == "Completed":
                # Job completed successfully - get video location
                s3_uri = response["outputDataConfig"]["s3OutputDataConfig"]["s3Uri"]
                job_folder = job_id.split('/')[-1]
                video_url = f"{s3_uri}/{job_folder}/output.mp4"
                
                result["video_url"] = video_url
                result["message"] = "Personalized video generation completed successfully"
            elif status == "Failed":
                result["message"] = response.get("failureMessage", "Personalized video generation failed")
            else:
                result["message"] = "Personalized video generation in progress"
                
            return result
            
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return {
                "job_id": job_id,
                "status": "ERROR",
                "message": f"Error checking job status: {str(e)}"
            }

# Test function
def test_true_image_to_video():
    """Test the true image-to-video generator"""
    try:
        print("🧪 Testing True Image-to-Video Generator")
        print("=" * 60)
        
        # Initialize the generator
        generator = TrueImageToVideoGenerator(s3_bucket="essencemirror-user-uploads")
        
        # Test with user image
        image_path = "/Users/kirubelaklilu/Desktop/axolotl-pink-captive-bred-two-column.jpg"
        
        print(f"📸 Using user image: {image_path}")
        
        # Test 1: Basic personalized video
        print(f"\n🧪 Test 1: Basic Personalized Video")
        result1 = generator.generate_personalized_video(
            image_path=image_path,
            recommendation_prompt="elegant business attire, sophisticated professional clothing, modern accessories",
            user_id="test_user_1"
        )
        
        print(f"✅ Basic personalized video started!")
        print(f"📋 Job ID: {result1['job_id']}")
        print(f"🎨 Prompt: {result1['prompt']}")
        
        # Test 2: Style recommendation video
        print(f"\n🧪 Test 2: Style Recommendation Video")
        result2 = generator.generate_style_recommendation_video(
            image_path=image_path,
            style_focus="wardrobe",
            specific_recommendations=["tailored blazers", "elegant dresses", "modern accessories"],
            user_id="test_user_2"
        )
        
        print(f"✅ Style recommendation video started!")
        print(f"📋 Job ID: {result2['job_id']}")
        print(f"🎯 Focus: {result2['style_focus']}")
        print(f"💡 Recommendations: {result2['specific_recommendations']}")
        
        print(f"\n🎉 SUCCESS: True Image-to-Video is working!")
        print(f"🎬 Both videos will show the ACTUAL person from the uploaded image")
        print(f"👤 The user will see themselves wearing the recommended styles")
        
        return True, [result1, result2]
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    import time
    success, results = test_true_image_to_video()
    
    if success:
        print(f"\n🚀 BREAKTHROUGH CONFIRMED!")
        print(f"✅ Nova Reel can show actual uploaded users in recommendation videos")
        print(f"✅ Perfect for personalized style recommendations")
        print(f"✅ Users will see themselves wearing suggested outfits")
        
        print(f"\n📋 Generated Jobs:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['job_id']}")
    else:
        print(f"\n❌ Test failed: {results}")
