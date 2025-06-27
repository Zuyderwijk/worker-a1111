import time
import runpod
import requests
import logging
import os
import sys
import base64
from io import BytesIO
from PIL import Image
import hashlib
from requests.adapters import HTTPAdapter, Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LOCAL_URL = "http://127.0.0.1:3000"
API_BASE = f"{LOCAL_URL}/sdapi/v1"

automatic_session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
automatic_session.mount('http://', HTTPAdapter(max_retries=retries))

# Cache for processed reference images and style consistency
reference_image_cache = {}
story_style_seed = None

# ---------------------------------------------------------------------------- #
#                              Dependency Checks                              #
# ---------------------------------------------------------------------------- #
def check_dependencies():
    """Check if required dependencies and files are available."""
    logger.info("Checking dependencies...")
    
    webui_paths = [
        "/workspace/stable-diffusion-webui",
        "/stable-diffusion-webui"
    ]
    
    webui_path = None
    for path in webui_paths:
        if os.path.exists(path):
            webui_path = path
            break
    
    if not webui_path:
        logger.error(f"Automatic1111 WebUI not found in any of: {webui_paths}")
        return False
    
    logger.info(f"Found WebUI at: {webui_path}")
    
    lora_dirs = [
        "/workspace/stable-diffusion-webui/models/Lora",
        "/stable-diffusion-webui/models/Lora"
    ]
    
    lora_dir_found = False
    for lora_dir in lora_dirs:
        if os.path.exists(lora_dir):
            lora_count = len([f for f in os.listdir(lora_dir) if f.endswith('.safetensors')])
            logger.info(f"Found LoRA directory: {lora_dir} with {lora_count} LoRA files")
            lora_dir_found = True
            break
    
    if not lora_dir_found:
        logger.warning("No LoRA directory found, will create when needed")
    
    logger.info("Dependencies check completed")
    return True


# ---------------------------------------------------------------------------- #
#                              Service Functions                              #
# ---------------------------------------------------------------------------- #
def wait_for_service(url, max_retries=300, retry_interval=2):
    """Check if the service is ready to receive requests."""
    health_check_url = f"{url}/sdapi/v1/options"
    logger.info(f"Waiting for WebUI API service at {health_check_url}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(health_check_url, timeout=10)
            if response.status_code == 200:
                logger.info("WebUI API service is ready!")
                return True
                
        except requests.exceptions.ConnectionError:
            if attempt % 15 == 0:
                logger.info(f"Service not ready yet. Attempt {attempt + 1}/{max_retries}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout waiting for service. Attempt {attempt + 1}/{max_retries}")
        except Exception as err:
            logger.error(f"Unexpected error checking service: {err}")
        
        time.sleep(retry_interval)
    
    logger.error(f"Service failed to start after {max_retries * retry_interval} seconds")
    return False


def validate_webui_startup():
    """Validate that WebUI is starting with correct parameters."""
    logger.info("Validating WebUI startup configuration...")
    try:
        response = requests.get(f"{LOCAL_URL}/internal/ping", timeout=5)
        logger.info("WebUI internal ping successful")
    except Exception:
        logger.warning("WebUI internal ping failed, but this might be normal")
    return True


# ---------------------------------------------------------------------------- #
#                        Story Generation Functions                            #
# ---------------------------------------------------------------------------- #
def get_image_hash(image_data):
    """Generate hash for image data to use as cache key"""
    if image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
    return hashlib.md5(image_data.encode()).hexdigest()


def process_reference_image(image_data, character_index=0):
    """Process reference image for character consistency"""
    try:
        cache_key = f"char_{character_index}_{get_image_hash(image_data)}"
        
        if cache_key in reference_image_cache:
            logger.info(f"Using cached reference image for character {character_index}")
            return reference_image_cache[cache_key]
        
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes)).convert('RGB')
        
        # High resolution sizing for print quality
        # Use larger dimensions that work well with SDXL/SD models
        target_size = (768, 768)  # Higher resolution for better print quality
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        processed_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Cache for consistency across scenes
        reference_image_cache[cache_key] = processed_b64
        logger.info(f"Cached reference image for character {character_index}")
        
        return processed_b64
        
    except Exception as e:
        logger.error(f"Error processing reference image: {e}")
        return None


def get_story_seed(story_id=None, reset=False):
    """
    Get or generate a consistent seed for the entire story
    This ensures style consistency across all scenes
    """
    global story_style_seed
    
    if reset or story_style_seed is None:
        if story_id:
            # Generate deterministic seed from story_id for reproducibility
            import hashlib
            story_style_seed = int(hashlib.md5(story_id.encode()).hexdigest()[:8], 16) % (2**31)
        else:
            # Generate random seed but keep it consistent for this story session
            import random
            story_style_seed = random.randint(1, 2**31-1)
        
        logger.info(f"Generated story seed: {story_style_seed}")
    
    return story_style_seed


def get_available_loras():
    """Get available LoRA models"""
    return [
        "3d_animation",
        "block_world", 
        "clay_animation",
        "geometric",
        "paper_cutout",
        "picture_book",
        "soft_anime",
        "whimsical_watercolor"
    ]


def get_lora_filename(lora_name):
    """Get the actual LoRA filename from available models"""
    try:
        lora_dirs = [
            "/workspace/stable-diffusion-webui/models/Lora",
            "/stable-diffusion-webui/models/Lora"
        ]
        
        available_loras = get_available_loras()
        
        if lora_name in available_loras:
            lora_filename = f"{lora_name}.safetensors"
            
            for lora_dir in lora_dirs:
                lora_path = os.path.join(lora_dir, lora_filename)
                if os.path.exists(lora_path):
                    logger.info(f"Using LoRA: {lora_filename}")
                    return lora_name
            
            logger.warning(f"LoRA file not found: {lora_filename}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting LoRA filename: {e}")
        return None


# ---------------------------------------------------------------------------- #
#                              Inference Functions                            #
# ---------------------------------------------------------------------------- #
def run_inference(inference_request, method="img2img"):
    """Run inference with proper error handling"""
    try:
        logger.info(f"Starting {method} inference")
        
        if method == "img2img":
            endpoint = f'{API_BASE}/img2img'
        else:
            endpoint = f'{API_BASE}/txt2img'
        
        response = automatic_session.post(
            url=endpoint,
            json=inference_request, 
            timeout=600
        )
        
        if response.status_code != 200:
            logger.error(f"Inference failed with status {response.status_code}: {response.text}")
            return {
                "error": f"API request failed with status {response.status_code}",
                "details": response.text
            }
        
        result = response.json()
        logger.info(f"{method} inference completed successfully")
        return {"images": result["images"]}
        
    except Exception as err:
        logger.error(f"Error in inference: {err}")
        return {"error": f"Inference failed: {str(err)}"}


def build_single_scene_request(scene_prompt, reference_images, story_config):
    """Build inference request for a single scene"""
    
    # Extract configuration
    story_style = story_config.get("story_style", "picture_book")
    lora_weight = story_config.get("lora_weight", 1.0)
    character_strength = story_config.get("character_strength", 0.65)
    story_id = story_config.get("story_id", "default")
    
    # Get consistent seed for this story
    seed = get_story_seed(story_id)
    
    # Build base prompt with style consistency
    full_prompt = f"{scene_prompt}, highly detailed, consistent style, professional illustration"
    
    # Base request with high-resolution settings for print quality
    request = {
        "prompt": full_prompt,
        "negative_prompt": story_config.get("negative_prompt", 
            "blurry, low quality, distorted, inconsistent style, ugly, deformed, different art style, pixelated, low resolution"),
        "steps": story_config.get("steps", 35),  # Higher steps for better quality
        "cfg_scale": story_config.get("cfg_scale", 7.5),
        "width": story_config.get("width", 768),   # Higher resolution for print
        "height": story_config.get("height", 768), # Square format good for storybooks
        "sampler_name": story_config.get("sampler_name", "DPM++ 2M Karras"),
        "seed": seed,  # CRITICAL: Same seed for style consistency
        "batch_size": 1,
        # Additional settings for print quality
        "restore_faces": True,  # Better face quality
        "tiling": False,
        "do_not_save_samples": True,
        "do_not_save_grid": True
    }
    
    # Add LoRA for story style
    if story_style and get_lora_filename(story_style):
        lora_trigger = f"<lora:{story_style}:{lora_weight}>"
        request["prompt"] = f"{request['prompt']}, {lora_trigger}"
        logger.info(f"Added LoRA for style consistency: {lora_trigger}")
    
    # Handle reference images for character consistency
    if reference_images and len(reference_images) > 0:
        # For now, use the first reference image
        # TODO: Could be enhanced to handle multiple characters per scene
        primary_reference = reference_images[0]
        processed_image = process_reference_image(primary_reference, 0)
        
        if processed_image:
            request["init_images"] = [processed_image]
            request["denoising_strength"] = character_strength
            return request, "img2img"
    
    return request, "txt2img"


def generate_story_batch(scene_prompts, reference_images, story_config):
    """
    Generate a complete story batch with consistent style and characters
    """
    try:
        results = []
        story_id = story_config.get("story_id", f"story_{int(time.time())}")
        
        # Reset seed for new story to ensure consistency within this story
        get_story_seed(story_id, reset=True)
        
        logger.info(f"Starting story generation: {len(scene_prompts)} scenes")
        
        for i, scene_prompt in enumerate(scene_prompts):
            logger.info(f"Generating scene {i+1}/{len(scene_prompts)}: {scene_prompt[:50]}...")
            
            # Build request for this scene
            inference_request, method = build_single_scene_request(
                scene_prompt, 
                reference_images, 
                story_config
            )
            
            # Generate the scene
            scene_result = run_inference(inference_request, method)
            
            # Add metadata
            scene_result["scene_index"] = i
            scene_result["scene_prompt"] = scene_prompt
            scene_result["method_used"] = method
            
            results.append(scene_result)
            
            # Small delay between scenes to avoid overwhelming the API
            if i < len(scene_prompts) - 1:
                time.sleep(1)
        
        logger.info(f"Story generation completed: {len(results)} scenes")
        
        return {
            "story_id": story_id,
            "total_scenes": len(scene_prompts),
            "scenes": results,
            "story_config": story_config,
            "style_seed_used": story_style_seed
        }
        
    except Exception as e:
        logger.error(f"Error in batch story generation: {e}")
        return {"error": f"Batch generation failed: {str(e)}"}


# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    """Main handler for story batch generation"""
    try:
        # Handle info/status requests
        if event.get("input", {}).get("action") == "get_info":
            return {
                "status": "ready",
                "service_type": "story_batch_generation",
                "available_loras": get_available_loras(),
                "api_endpoint": API_BASE,
                "supported_methods": ["single_scene", "story_batch"],
                "features": [
                    "batch_story_generation",
                    "character_consistency_via_reference_images",
                    "style_consistency_via_seed_locking",
                    "multiple_scene_prompts",
                    "lora_style_control"
                ],
                "input_format": {
                    "scene_prompts": "array of strings - descriptions for each scene",
                    "reference_images": "array of base64 images - character references",
                    "story_style": "string - LoRA name for artistic style",
                    "story_id": "string - unique identifier for reproducibility",
                    "print_optimized": "bool - optimized for high-quality print output at 768x768",
                    "recommended_dimensions": "768x768 (optimized for print upscaling to 300 DPI)"
                }
            }
        
        # Validate input
        if "input" not in event:
            return {"error": "No input provided"}
        
        input_data = event["input"]
        
        # Check if this is a batch story request
        scene_prompts = input_data.get("scene_prompts", [])
        
        if scene_prompts and len(scene_prompts) > 0:
            # BATCH STORY GENERATION
            reference_images = input_data.get("reference_images", [])
            
            story_config = {
                "story_style": input_data.get("story_style", "picture_book"),
                "story_id": input_data.get("story_id"),
                "lora_weight": input_data.get("lora_weight", 1.0),
                "character_strength": input_data.get("character_strength", 0.65),
                "steps": input_data.get("steps", 35),  # Higher for print quality
                "cfg_scale": input_data.get("cfg_scale", 7.5),
                "width": input_data.get("width", 768),   # Print-optimized resolution
                "height": input_data.get("height", 768), # Print-optimized resolution
                "negative_prompt": input_data.get("negative_prompt"),
                "sampler_name": input_data.get("sampler_name", "DPM++ 2M Karras")
            }
            
            # Generate the complete story
            result = generate_story_batch(scene_prompts, reference_images, story_config)
            return result
            
        else:
            # SINGLE SCENE GENERATION (fallback)
            scene_prompt = input_data.get("prompt") or input_data.get("scene_prompt")
            if not scene_prompt:
                return {"error": "Either 'scene_prompts' array or single 'prompt' is required"}
            
            reference_images = input_data.get("reference_images", [])
            story_config = {
                "story_style": input_data.get("story_style", "picture_book"),
                "story_id": input_data.get("story_id"),
                "lora_weight": input_data.get("lora_weight", 1.0),
                "character_strength": input_data.get("character_strength", 0.65),
                "steps": input_data.get("steps", 35),  # Higher for print quality
                "cfg_scale": input_data.get("cfg_scale", 7.5),
                "width": input_data.get("width", 768),   # Print-optimized resolution
                "height": input_data.get("height", 768), # Print-optimized resolution
                "negative_prompt": input_data.get("negative_prompt"),
                "sampler_name": input_data.get("sampler_name", "DPM++ 2M Karras")
            }
            
            inference_request, method = build_single_scene_request(
                scene_prompt, reference_images, story_config
            )
            
            result = run_inference(inference_request, method)
            result["method_used"] = method
            result["story_config"] = story_config
            
            return result
        
    except Exception as err:
        logger.error(f"Handler error: {err}")
        return {"error": f"Handler failed: {str(err)}"}


if __name__ == "__main__":
    logger.info("Starting Story Batch Generation Worker...")
    
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    if not validate_webui_startup():
        logger.error("WebUI startup validation failed. Exiting.")
        sys.exit(1)
    
    if not wait_for_service(url=LOCAL_URL):
        logger.error("WebUI API service failed to start. Exiting.")
        sys.exit(1)
    
    logger.info("Story Batch Generation Service is ready. Starting RunPod Serverless...")
    runpod.serverless.start({"handler": handler})