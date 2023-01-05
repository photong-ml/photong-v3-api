"""
Main application file for the API.
"""

import os
from typing import Optional

import dotenv
from fastapi import FastAPI, UploadFile

from utils import pipeline, components
from utils.schemas import (
    HealthResponse,
    InferenceResponse,
    InferencePromptResponse,
)

dotenv.load_dotenv()

azure_key = os.getenv("AZURE_KEY", "")
assert azure_key, "AZURE_KEY is not set."
azure_endpoint = os.getenv("AZURE_ENDPOINT", "")
assert azure_endpoint, "AZURE_ENDPOINT is not set."
hf_token = os.getenv("HF_TOKEN", "")
assert hf_token, "HF_TOKEN is not set."

app = FastAPI(
    title="Photong v4 API",
    description="The backend generator for Photong v4.",
    version="4.0.0",
    openapi_tags=[
        {"name": "Root", "description": "Root endpoint for the API."},
        {
            "name": "Inference",
            "description": "Endpoints for generating music and image captions.",
        },
    ],
)


@app.get("/", tags=["Root"], response_model=HealthResponse)
async def root() -> dict[str, str]:
    """
    Root endpoint for the API.
    """
    return {"message": "Server is running."}


@app.post("/infer", tags=["Inference"], response_model=InferenceResponse)
async def infer(
    file: UploadFile, seed: int, seed_img: Optional[str] = None
) -> dict[str, str | float]:
    """
    Generate music from an image.
    """
    img = await file.read()
    return pipeline.image_to_music(
        img,
        azure_key=azure_key,
        azure_endpoint=azure_endpoint,
        hf_token=hf_token,
        riffusion_seed=seed,
        riffusion_seed_img=seed_img,
    )


@app.post(
    "/infer/with-prompt", tags=["Inference"], response_model=InferencePromptResponse
)
async def infer_with_prompt(
    prompt: str, seed: int, seed_img: Optional[str] = None
) -> dict[str, str | float]:
    """
    Generate music from a prompt.
    """
    audio, duration = components.generate_music(
        prompt,
        seed=seed,
        seed_img=seed_img,
    )
    return {
        "audio": audio,
        "duration": duration,
    }
