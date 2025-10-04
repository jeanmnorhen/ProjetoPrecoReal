import os
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult

from .celery_worker import process_product_image
from .schemas import TaskTicket, TaskStatus

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Serviço de Agentes de IA",
    description="API para processamento de catálogo de produtos com LLM local.",
    version="1.0.0"
)

# --- CORS Configuration ---
# As per the plan, allow Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for now, can be restricted to Vercel regex
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Directory for Uploads ---
# This path must be a shared volume in Docker
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# --- API Endpoints ---

@app.post("/api/agents/catalog-intake", response_model=TaskTicket, status_code=202)
async def catalog_intake(file: UploadFile = File(...)):
    """
    Accepts a product image, saves it, and dispatches a processing task to Celery.
    """
    try:
        # Generate a unique filename to avoid collisions
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        # Save the uploaded file to the shared volume
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Dispatch the task to the Celery worker, passing the file path
        task = process_product_image.delay(str(file_path))

        return {"task_id": task.id, "status": "PENDING"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


@app.get("/api/agents/task-status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    Checks the status of a Celery task.
    """
    task_result = AsyncResult(task_id)

    if task_result.ready():
        if task_result.successful():
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "result": task_result.result,
                "error": None
            }
        else:
            # The result of a failed task is the exception that was raised
            error_info = str(task_result.result)
            return {
                "task_id": task_id,
                "status": "FAILURE",
                "result": None,
                "error": error_info
            }
    else:
        return {
            "task_id": task_id,
            "status": "PENDING",
            "result": None,
            "error": None
        }

@app.get("/api/health")
def health_check():
    # A simple health check for the API itself
    return {"status": "ok"}
