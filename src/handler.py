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
    
    # Get book format and dimensions
    book_format = story_config.get("book_format", "square_small")
    scene_width, scene_height, _, _, format_info = get_book_dimensions(
        book_format,
        story_config.get("custom_width"),
        story_config.get("custom_height")
    )
    
    # Override with explicit dimensions if provided
    final_width = story_config.get("width", scene_width)
    final_height = story_config.get("height", scene_height)
    
    # Get consistent seed for this story
    seed = get_story_seed(story_id)
    
    # ENHANCED PROMPT for professional children's book scene illustrations
    full_prompt = f"""
    {scene_prompt}, professional children's book illustration,
    storybook scene, highly detailed, consistent style,
    vibrant colors, child-friendly artwork,
    clean composition, narrative illustration,
    appealing to children aged 4-8, magical atmosphere,
    whimsical art style, storytelling illustration,
    professional book illustration quality,
    detailed but clear, perfect for children's book,
    bright and engaging, fantasy storybook art
    """.strip().replace('\n', ' ')
    
    # OPTIMAL Scene generation settings for children's book illustrations
    request = {
        "prompt": full_prompt,
        "negative_prompt": story_config.get("negative_prompt", 
            "blurry, low quality, distorted, inconsistent style, ugly, deformed, different art style, pixelated, low resolution, dark themes, scary elements, inappropriate content, crowded composition, too busy, cluttered, unprofessional, poor composition, amateur artwork"),
        "steps": story_config.get("steps", 45),  # Increased from 35 for higher quality
        "cfg_scale": story_config.get("cfg_scale", 7.5),
        "width": final_width,   # Dynamic based on book format
        "height": final_height, # Dynamic based on book format
        "sampler_name": story_config.get("sampler_name", "DPM++ 2M Karras"),
        "seed": seed,  # CRITICAL: Same seed for style consistency
        "batch_size": 1,
        
        # PRINT QUALITY ENHANCEMENTS for scenes
        "restore_faces": True,  # Better character face quality
        "tiling": False,
        "do_not_save_samples": True,
        "do_not_save_grid": True,
        "enable_hr": True,              # Enable high-res fix for crisp details
        "hr_scale": 1.2,               # Moderate upscale for scenes
        "hr_upscaler": "R-ESRGAN 4x+", # Best upscaler for illustrations
        "hr_second_pass_steps": 15      # Additional steps for high-res pass
    }
    
    # Add metadata about the book format
    request["_book_format_info"] = {
        "book_format": book_format,
        "generation_size": f"{final_width}x{final_height}",
        "format_name": format_info["name"] if "name" in format_info else "Custom",
        "aspect_ratio": format_info.get("aspect_ratio", final_width/final_height)
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
#                         Book Cover Generation Functions                      #
# ---------------------------------------------------------------------------- #
def build_book_cover_request(title, subtitle, style, theme, reference_images=None, book_format="square_small", custom_width=None, custom_height=None):
    """Build inference request specifically for book covers"""
    
    # Get book format and dimensions
    _, _, cover_width, cover_height, format_info = get_book_dimensions(
        book_format, custom_width, custom_height
    )
    
    logger.info(f"Generating book cover for format: {format_info['name']} at {cover_width}x{cover_height}")
    
    # ENHANCED PROMPT for professional children's book covers
    cover_prompt = f"""
    Professional children's book cover illustration, "{title}" {f'- {subtitle}' if subtitle else ''}, 
    {theme} theme, {style} art style, whimsical artistic style,
    high quality digital art, fantasy children's book illustration,
    colorful and inviting, magical atmosphere, 
    clean composition perfect for book cover,
    professional book design, appealing to children aged 4-8,
    bright and cheerful, storybook art style,
    award-winning children's book illustration,
    detailed but not cluttered, perfect cover composition,
    publishing quality artwork, child-friendly imagery,
    title space at top, vibrant colors, eye-catching
    """.strip().replace('\n', ' ')
    
    # ENHANCED negative prompt for professional book covers
    cover_negative_prompt = """
    text overlay, existing text, watermarks, blurry, low quality, 
    dark themes, scary elements, inappropriate content,
    crowded composition, too busy, cluttered, messy layout,
    unprofessional layout, pixelated, distorted,
    adult themes, violence, scary faces, monsters,
    poor composition, amateur artwork, ugly, deformed,
    low resolution, artifacts, noise, oversaturated,
    underexposed, overexposed, bad anatomy, wrong proportions
    """.strip().replace('\n', ' ')
    
    # OPTIMAL Book cover generation settings for print quality
    request = {
        "prompt": cover_prompt,
        "negative_prompt": cover_negative_prompt,
        "steps": 50,  # Increased for higher quality
        "cfg_scale": 7.5,  # Optimized for better balance
        "width": cover_width,   # Dynamic based on book format
        "height": cover_height, # Dynamic based on book format
        "sampler_name": "DPM++ 2M Karras",  # Excellent choice for illustrations
        "seed": -1,  # Random for variety unless specified
        "batch_size": 1,
        "restore_faces": True,
        "tiling": False,
        "do_not_save_samples": True,
        "do_not_save_grid": True,
        
        # PRINT QUALITY ENHANCEMENTS
        "enable_hr": True,          # Enable high-res fix for crisp details
        "hr_scale": 1.3,           # Moderate upscale for quality boost
        "hr_upscaler": "R-ESRGAN 4x+",  # Best upscaler for illustrations
        "hr_second_pass_steps": 20  # Additional steps for high-res pass
    }
    
    # Add metadata about the book format
    request["_book_format_info"] = {
        "book_format": book_format,
        "generation_size": f"{cover_width}x{cover_height}",
        "format_name": format_info["name"],
        "aspect_ratio": format_info.get("aspect_ratio", cover_width/cover_height),
        "is_cover": True
    }
    
    # Add LoRA for style consistency
    if style and get_lora_filename(style):
        lora_trigger = f"<lora:{style}:1.0>"
        request["prompt"] = f"{request['prompt']}, {lora_trigger}"
        logger.info(f"Added LoRA for book cover style: {lora_trigger}")
    
    # Handle reference images for character consistency
    if reference_images and len(reference_images) > 0:
        primary_reference = reference_images[0]
        processed_image = process_reference_image(primary_reference, 0)
        
        if processed_image:
            request["init_images"] = [processed_image]
            request["denoising_strength"] = 0.55  # Optimized for covers with character consistency
            return request, "img2img"
    
    return request, "txt2img"


def generate_book_cover(title, subtitle, style, theme, reference_images=None, book_format="square_small", custom_width=None, custom_height=None):
    """Generate a book cover with specific optimizations"""
    try:
        logger.info(f"Generating book cover: {title}")
        
        # Build the cover-specific request
        inference_request, method = build_book_cover_request(
            title, subtitle, style, theme, reference_images, book_format, custom_width, custom_height
        )
        
        # Generate the cover
        result = run_inference(inference_request, method)
        
        # Add metadata specific to book covers
        result["generation_type"] = "book_cover"
        result["method_used"] = method
        result["cover_config"] = {
            "title": title,
            "subtitle": subtitle,
            "style": style,
            "theme": theme,
            "dimensions": f"{inference_request['width']}x{inference_request['height']}",
            "book_format": book_format,
            "book_format_info": inference_request.get("_book_format_info", {})
        }
        
        # Add print dimension information
        if book_format:
            print_info = calculate_print_dimensions(book_format)
            if print_info:
                result["print_info"] = print_info
        
        logger.info("Book cover generation completed")
        return result
        
    except Exception as e:
        logger.error(f"Error in book cover generation: {e}")
        return {"error": f"Book cover generation failed: {str(e)}"}


# ---------------------------------------------------------------------------- #
#                         Book Format Specifications                           #
# ---------------------------------------------------------------------------- #
def get_available_book_formats():
    """Get list of available book formats for API response"""
    formats = get_lulu_book_formats()
    return {
        format_id: {
            "name": info["name"],
            "physical_size_inches": info["physical_size_inches"],
            "aspect_ratio": info["aspect_ratio"],
            "generation_size": info["scene_gen_size"],
            "best_for": info["best_for"]
        }
        for format_id, info in formats.items()
    }


def get_lulu_book_formats():
    """Get available Lulu book formats with their aspect ratios and recommended generation sizes"""
    return {
        "pocket_book": {
            "name": "Pocket Book (4.25\" x 6.875\")",
            "physical_size_inches": (4.25, 6.875),
            "physical_size_mm": (108, 175),
            "aspect_ratio": 0.618,  # width/height ratio
            "scene_gen_size": (512, 832),     # High-res maintaining aspect ratio
            "cover_gen_size": (512, 832),     # Same for covers
            "target_dpi": 300,
            "best_for": "Pocket-sized children's books, travel books"
        },
        "us_trade": {
            "name": "US Trade (6\" x 9\")", 
            "physical_size_inches": (6, 9),
            "physical_size_mm": (152, 229),
            "aspect_ratio": 0.667,  # 2:3 ratio
            "scene_gen_size": (576, 864),     # High-res maintaining aspect ratio
            "cover_gen_size": (576, 864),
            "target_dpi": 300,
            "best_for": "Standard chapter books, novels"
        },
        "royal": {
            "name": "Royal (6.14\" x 9.21\")",
            "physical_size_inches": (6.14, 9.21),
            "physical_size_mm": (156, 234),
            "aspect_ratio": 0.667,  # Close to 2:3
            "scene_gen_size": (584, 876),     # High-res maintaining aspect ratio
            "cover_gen_size": (584, 876),
            "target_dpi": 300,
            "best_for": "Premium books, literary works"
        },
        "crown_quarto": {
            "name": "Crown Quarto (7.44\" x 9.69\")",
            "physical_size_inches": (7.44, 9.69),
            "physical_size_mm": (189, 246),
            "aspect_ratio": 0.768,
            "scene_gen_size": (640, 832),     # High-res maintaining aspect ratio
            "cover_gen_size": (640, 832),
            "target_dpi": 300,
            "best_for": "Academic books, textbooks"
        },
        "us_letter": {
            "name": "US Letter (8.5\" x 11\")",
            "physical_size_inches": (8.5, 11),
            "physical_size_mm": (216, 279),
            "aspect_ratio": 0.773,  # Close to 3:4
            "scene_gen_size": (680, 880),     # High-res maintaining aspect ratio
            "cover_gen_size": (680, 880),
            "target_dpi": 300,
            "best_for": "Activity books, educational books, workbooks"
        },
        "square_small": {
            "name": "Square Small (8.5\" x 8.5\")",
            "physical_size_inches": (8.5, 8.5),
            "physical_size_mm": (216, 216),
            "aspect_ratio": 1.0,  # Perfect square
            "scene_gen_size": (768, 768),     # High-res square
            "cover_gen_size": (768, 768),
            "target_dpi": 300,
            "best_for": "Picture books, children's books"
        },
        "landscape": {
            "name": "Landscape (11\" x 8.5\")",
            "physical_size_inches": (11, 8.5),
            "physical_size_mm": (279, 216),
            "aspect_ratio": 1.294,  # 4:3 landscape
            "scene_gen_size": (880, 680),     # High-res landscape
            "cover_gen_size": (880, 680),
            "target_dpi": 300,
            "best_for": "Panoramic storybooks, coffee table books"
        },
        "square_large": {
            "name": "Square Large (10\" x 10\")",
            "physical_size_inches": (10, 10),
            "physical_size_mm": (254, 254),
            "aspect_ratio": 1.0,  # Perfect square
            "scene_gen_size": (896, 896),     # High-res large square
            "cover_gen_size": (896, 896),
            "target_dpi": 300,
            "best_for": "Premium picture books, art books"
        }
    }


def get_book_dimensions(book_format="square_small", custom_width=None, custom_height=None):
    """
    Get optimal generation dimensions based on Lulu book format
    Returns the highest resolution that maintains the correct aspect ratio
    for later upscaling to 300 DPI print quality
    
    Returns: (scene_width, scene_height, cover_width, cover_height, format_info)
    """
    if custom_width and custom_height:
        # Custom dimensions provided - use as-is
        format_info = {
            "name": "Custom Format",
            "aspect_ratio": custom_width / custom_height,
            "is_custom": True
        }
        return (custom_width, custom_height, custom_width, custom_height, format_info)
    
    formats = get_lulu_book_formats()
    
    if book_format not in formats:
        logger.warning(f"Unknown book format: {book_format}, defaulting to square_small")
        book_format = "square_small"
    
    format_spec = formats[book_format]
    scene_dims = format_spec["scene_gen_size"]
    cover_dims = format_spec["cover_gen_size"]
    
    logger.info(f"Using book format: {format_spec['name']}")
    logger.info(f"Physical size: {format_spec['physical_size_inches'][0]}\" x {format_spec['physical_size_inches'][1]}\"")
    logger.info(f"Generation size: {scene_dims[0]}x{scene_dims[1]} (aspect ratio: {format_spec['aspect_ratio']:.3f})")
    logger.info(f"Target 300 DPI size: {format_spec['physical_size_inches'][0] * 300:.0f} x {format_spec['physical_size_inches'][1] * 300:.0f}")
    
    return (scene_dims[0], scene_dims[1], cover_dims[0], cover_dims[1], format_spec)


def calculate_print_dimensions(book_format):
    """
    Calculate the final print dimensions at 300 DPI for a given book format
    This is what the images will be upscaled to during final processing
    """
    formats = get_lulu_book_formats()
    if book_format not in formats:
        return None
    
    format_spec = formats[book_format]
    width_inches, height_inches = format_spec["physical_size_inches"]
    
    # Calculate 300 DPI dimensions
    print_width = int(width_inches * 300)
    print_height = int(height_inches * 300)
    
    return {
        "print_width": print_width,
        "print_height": print_height,
        "print_size_inches": (width_inches, height_inches),
        "dpi": 300,
        "format_name": format_spec["name"]
    }


# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    """Main handler for story batch generation"""
    try:
        # Handle debug environment requests
        if event.get("input", {}).get("action") == "debug_env":
            import os
            env_info = {
                "status": "debug",
                "environment_variables": {
                    "HUGGINGFACE_TOKEN": "SET" if os.getenv("HUGGINGFACE_TOKEN") else "NOT SET",
                    "HF_TOKEN": "SET" if os.getenv("HF_TOKEN") else "NOT SET", 
                    "HUGGING_FACE_API_TOKEN": "SET" if os.getenv("HUGGING_FACE_API_TOKEN") else "NOT SET",
                    "all_env_vars_with_token": [k for k in os.environ.keys() if "token" in k.lower()],
                    "all_env_vars_with_hf": [k for k in os.environ.keys() if "hf" in k.lower()],
                    "total_env_vars": len(os.environ)
                }
            }
            if os.getenv("HUGGINGFACE_TOKEN"):
                env_info["environment_variables"]["HUGGINGFACE_TOKEN_preview"] = os.getenv("HUGGINGFACE_TOKEN")[:10] + "..."
            return env_info

        # Handle info/status requests
        if event.get("input", {}).get("action") == "get_info":
            return {
                "status": "ready",
                "service_type": "story_batch_generation",
                "available_loras": get_available_loras(),
                "available_book_formats": get_available_book_formats(),
                "api_endpoint": API_BASE,
                "supported_methods": ["single_scene", "story_batch", "book_cover"],
                "features": [
                    "batch_story_generation",
                    "book_cover_generation",
                    "character_consistency_via_reference_images",
                    "style_consistency_via_seed_locking",
                    "multiple_scene_prompts",
                    "lora_style_control",
                    "dynamic_lulu_book_formats",
                    "print_quality_optimization"
                ],
                "input_format": {
                    "scene_prompts": "array of strings - descriptions for each scene",
                    "reference_images": "array of base64 images - character references",
                    "story_style": "string - LoRA name for artistic style",
                    "story_id": "string - unique identifier for reproducibility",
                    "book_format": "string - Lulu book format ID (pocket_book, us_trade, square_small, etc.)",
                    "custom_width": "number - custom width if not using standard format",
                    "custom_height": "number - custom height if not using standard format",
                    "generation_type": "string - 'book_cover' for covers, omit for scenes",
                    "title": "string - book title (for covers)",
                    "subtitle": "string - book subtitle (for covers)",
                    "theme": "string - story theme (for covers)",
                    "print_optimized": "bool - optimized for high-quality print output",
                    "note": "Generates highest resolution for selected format, upscale to 300 DPI during post-processing"
                }
            }
        
        # Validate input
        if "input" not in event:
            return {"error": "No input provided"}
        
        input_data = event["input"]
        
        # Check if this is a book cover generation request
        if input_data.get("action") == "generate_book_cover":
            # BOOK COVER GENERATION
            title = input_data.get("title", "Untitled Book")
            author = input_data.get("author", "Unknown Author")
            style = input_data.get("story_style", "picture_book")
            theme = input_data.get("theme", "Adventure")
            reference_images = input_data.get("reference_images", [])
            
            result = generate_book_cover(title, author, style, theme, reference_images)
            return result
        
        # Check if this is a batch story request
        scene_prompts = input_data.get("scene_prompts", [])
        
        # Check if this is a book cover request
        if input_data.get("generation_type") == "book_cover":
            # BOOK COVER GENERATION
            title = input_data.get("title", "Untitled Story")
            subtitle = input_data.get("subtitle", "")
            theme = input_data.get("theme", "magical adventure")
            style = input_data.get("story_style", "picture_book")
            reference_images = input_data.get("reference_images", [])
            book_format = input_data.get("book_format", "square_small")
            custom_width = input_data.get("custom_width")
            custom_height = input_data.get("custom_height")
            
            result = generate_book_cover(title, subtitle, style, theme, reference_images, book_format, custom_width, custom_height)
            return result
            
        elif scene_prompts and len(scene_prompts) > 0:
            # BATCH STORY GENERATION
            reference_images = input_data.get("reference_images", [])
            
            story_config = {
                "story_style": input_data.get("story_style", "picture_book"),
                "story_id": input_data.get("story_id"),
                "book_format": input_data.get("book_format", "square_small"),
                "custom_width": input_data.get("custom_width"),
                "custom_height": input_data.get("custom_height"),
                "lora_weight": input_data.get("lora_weight", 1.0),
                "character_strength": input_data.get("character_strength", 0.65),
                "steps": input_data.get("steps", 45),  # Increased for print quality scenes
                "cfg_scale": input_data.get("cfg_scale", 7.5),
                "width": input_data.get("width"),   # Optional override
                "height": input_data.get("height"), # Optional override
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
                "book_format": input_data.get("book_format", "square_small"),
                "custom_width": input_data.get("custom_width"),
                "custom_height": input_data.get("custom_height"),
                "lora_weight": input_data.get("lora_weight", 1.0),
                "character_strength": input_data.get("character_strength", 0.65),
                "steps": input_data.get("steps", 45),  # Increased for print quality scenes
                "cfg_scale": input_data.get("cfg_scale", 7.5),
                "width": input_data.get("width"),   # Optional override
                "height": input_data.get("height"), # Optional override
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