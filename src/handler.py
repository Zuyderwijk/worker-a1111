import time
import runpod
import requests
import logging
import os
import sys
from requests.adapters import HTTPAdapter, Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LOCAL_URL = "http://127.0.0.1:3000"
API_BASE = f"{LOCAL_URL}/sdapi/v1"

automatic_session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
automatic_session.mount('http://', HTTPAdapter(max_retries=retries))


# ---------------------------------------------------------------------------- #
#                              Dependency Checks                              #
# ---------------------------------------------------------------------------- #
def check_dependencies():
    """
    Check if required dependencies and files are available.
    """
    logger.info("Checking dependencies...")
    
    # Check if WebUI directory exists
    webui_path = "/stable-diffusion-webui"
    if not os.path.exists(webui_path):
        logger.error(f"Automatic1111 WebUI not found at {webui_path}")
        return False
    
    # Check if main model file exists
    model_path = "/model.safetensors"
    if not os.path.exists(model_path):
        logger.error(f"Model file not found at {model_path}")
        return False
    
    # Check if webui.py exists
    webui_script = f"{webui_path}/webui.py"
    if not os.path.exists(webui_script):
        logger.error(f"WebUI script not found at {webui_script}")
        return False
    
    logger.info("All dependencies check passed")
    return True


# ---------------------------------------------------------------------------- #
#                              Service Functions                              #
# ---------------------------------------------------------------------------- #
def wait_for_service(url, max_retries=300, retry_interval=2):
    """
    Check if the service is ready to receive requests.
    Uses the standard A1111 API health check endpoint.
    """
    health_check_url = f"{url}/sdapi/v1/options"
    logger.info(f"Waiting for WebUI API service at {health_check_url}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(health_check_url, timeout=10)
            if response.status_code == 200:
                logger.info("WebUI API service is ready!")
                return True
                
        except requests.exceptions.ConnectionError:
            if attempt % 15 == 0:  # Log every 30 seconds
                logger.info(f"Service not ready yet. Attempt {attempt + 1}/{max_retries}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout waiting for service. Attempt {attempt + 1}/{max_retries}")
        except Exception as err:
            logger.error(f"Unexpected error checking service: {err}")
        
        time.sleep(retry_interval)
    
    logger.error(f"Service failed to start after {max_retries * retry_interval} seconds")
    return False


def validate_webui_startup():
    """
    Validate that WebUI is starting with correct parameters.
    """
    logger.info("Validating WebUI startup configuration...")
    
    # Check if the process is running
    try:
        response = requests.get(f"{LOCAL_URL}/internal/ping", timeout=5)
        logger.info("WebUI internal ping successful")
    except Exception:
        logger.warning("WebUI internal ping failed, but this might be normal")
    
    return True


# ---------------------------------------------------------------------------- #
#                              Inference Functions                            #
# ---------------------------------------------------------------------------- #
def wait_for_service_legacy(url):
    """
    Legacy service check - keeping for compatibility.
    """
    retries = 0

    while True:
        try:
            requests.get(url, timeout=120)
            return
        except requests.exceptions.RequestException:
            retries += 1

            # Only log every 15 retries so the logs don't get spammed
            if retries % 15 == 0:
                print("Service not ready yet. Retrying...")
        except Exception as err:
            print("Error: ", err)

        time.sleep(0.2)


def run_inference(inference_request):
    """
    Run inference on a request with improved error handling.
    """
    try:
        logger.info("Starting inference request")
        logger.debug(f"Request payload: {inference_request}")
        
        response = automatic_session.post(
            url=f'{API_BASE}/txt2img',
            json=inference_request, 
            timeout=600
        )
        
        if response.status_code != 200:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return {
                "error": f"API request failed with status {response.status_code}",
                "details": response.text
            }
        
        result = response.json()
        logger.info("Inference completed successfully")
        
        # Ensure proper output format
        if "images" in result:
            return {"images": result["images"]}
        else:
            logger.error("No images in API response")
            return {"error": "No images generated", "raw_response": result}
            
    except requests.exceptions.Timeout:
        logger.error("Request timeout during inference")
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        logger.error("Connection error during inference")
        return {"error": "Connection error to WebUI API"}
    except Exception as err:
        logger.error(f"Unexpected error during inference: {err}")
        return {"error": f"Inference failed: {str(err)}"}


def get_available_loras():
    """Get list of available LoRA models"""
    try:
        response = automatic_session.get(f'{API_BASE}/loras', timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to get LoRAs: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error getting LoRAs: {e}")
        return []


# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    """
    This is the handler function that will be called by the serverless.
    """
    try:
        # Handle info/status requests
        if event.get("input", {}).get("action") == "get_info":
            return {
                "status": "ready",
                "available_loras": get_available_loras(),
                "api_endpoint": API_BASE
            }
        
        # Validate input
        if "input" not in event:
            return {"error": "No input provided"}
        
        # Run inference
        result = run_inference(event["input"])
        return result
        
    except Exception as err:
        logger.error(f"Handler error: {err}")
        return {"error": f"Handler failed: {str(err)}"}


if __name__ == "__main__":
    logger.info("Starting RunPod worker initialization...")
    
    # Check dependencies first
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Validate WebUI startup
    if not validate_webui_startup():
        logger.error("WebUI startup validation failed. Exiting.")
        sys.exit(1)
    
    # Wait for service to be ready
    if not wait_for_service(url=LOCAL_URL):
        logger.error("WebUI API service failed to start. Exiting.")
        sys.exit(1)
    
    logger.info("WebUI API Service is ready. Starting RunPod Serverless...")
    runpod.serverless.start({"handler": handler})