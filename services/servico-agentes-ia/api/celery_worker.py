import os
from celery import Celery
from llama_cpp import Llama
from llama_cpp.llama_chat_format import MoondreamChatFormat
import instructor
import cv2
import numpy as np
import base64
from .schemas import ProductData

# --- Celery Configuration ---
# The broker URL is taken from the environment variable set in docker-compose.yml
celery_app = Celery(
    'tasks',
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)

# --- Global Model Variable ---
# This dictionary will hold the loaded models. Loading happens once when the worker starts.
models = {}

def load_models():
    """
    Loads the LLM and VLM models into memory.
    This function is called once when the Celery worker process starts.
    """
    print("Loading models into memory...")
    
    # Configure and load the Vision-Language-Model (BakLLaVA)
    # The projector file (mmproj) is crucial for the vision capabilities.
    chat_handler = MoondreamChatFormat.from_gguf(
        mmproj_path="/app/models/mmproj-model-f16.gguf"
    )
    
    models['vision_llm'] = Llama(
        model_path="/app/models/bakllava-1-7b.Q4_K_M.gguf",
        chat_handler=chat_handler,
        n_ctx=2048,
        n_threads=int(os.environ.get("N_THREADS", 6)),
        n_gpu_layers=int(os.environ.get("N_GPU_LAYERS", 0)) # 0 for CPU-only
    )
    
    # Patch the client to enable structured output with Pydantic
    models['patched_vision_client'] = instructor.patch(
        client=models['vision_llm'],
        mode=instructor.Mode.JSON
    )
    print("Models loaded successfully.")

# Load models when the worker starts
load_models()

@celery_app.task(name='process_product_image')
def process_product_image(image_path: str) -> dict:
    """
    Celery task to process a product image and generate structured data.
    """
    try:
        print(f"Processing image at path: {image_path}")
        
        # 1. Pre-process the image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Could not read image from path.")
            
        # Example pre-processing: resize
        # A real implementation would have more steps as per the plan (normalization, etc.)
        image = cv2.resize(image, (336, 336))
        
        # Convert to base64 to pass to the model
        _, buffer = cv2.imencode('.jpg', image)
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # 2. Run inference using the loaded and patched model
        client = models.get('patched_vision_client')
        if not client:
            raise RuntimeError("Vision model is not loaded.")

        prompt = (
            "You are an expert product cataloger. Analyze the following image of a product "
            "and generate the structured data based on the Pydantic schema. "
            "Provide a concise, SEO-friendly product name, a standard high-level category, "
            "a detailed description of at least 50 words, and a list of 3-5 key features."
        )
        
        response = client.chat.completions.create(
            response_model=ProductData,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
            max_retries=3, # Use instructor's retry mechanism
        )
        
        print("Inference successful. Cleaning up image file.")
        os.remove(image_path) # Clean up the uploaded file
        
        return response.model_dump()

    except Exception as e:
        print(f"An error occurred in the Celery task: {e}")
        # Clean up the file even if an error occurs
        if os.path.exists(image_path):
            os.remove(image_path)
        # Re-raise the exception so Celery marks the task as FAILED
        raise e
