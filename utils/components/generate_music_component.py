"""
Generate music from a prompt.

This is a modified version of the Riffusion server code.
See https://github.com/riffusion/riffusion/blob/main/riffusion/server.py
"""
import io
import sys
from pathlib import Path
from typing import Optional

import dacite.core
import torch
from PIL import Image

RIFFUSION_LIB_PATH = Path(__file__).parent / "libriffusion"
CHECKPOINT = "riffusion/riffusion-model-v1"

sys.path.append(str(RIFFUSION_LIB_PATH))

# pylint: disable=import-error, wrong-import-position
# skipcq: FLK-E402
from .libriffusion.riffusion.datatypes import InferenceInput

# skipcq: FLK-E402
from .libriffusion.riffusion.riffusion_pipeline import RiffusionPipeline

# skipcq: FLK-E402
from .libriffusion.riffusion.spectrogram_image_converter import (
    SpectrogramImageConverter,
)

# skipcq: FLK-E402
from .libriffusion.riffusion.spectrogram_params import SpectrogramParams

# skipcq: FLK-E402
from .libriffusion.riffusion.util import base64_util

# pylint: enable=import-error, wrong-import-position

sys.path.pop()

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
PIPELINE = RiffusionPipeline.load_checkpoint(
    checkpoint=CHECKPOINT,
    device=DEVICE,
)
converter = SpectrogramImageConverter(
    params=SpectrogramParams(
        min_frequency=0,
        max_frequency=10000,
    ),
    device=DEVICE,
)


def generate_music(
    prompt: str, seed: int, alpha: float, seed_img: Optional[str] = "og_beat"
) -> tuple[str, float]:
    """
    Generate music from a prompt using the Riffusion API.

    Parameters:
        prompt (str): The prompt to use.
        seed (int): The seed to use.
        alpha (float): The alpha to use.
        seed_img (Optional[str]): The seed image to use.

    Returns:
        tuple[str, float]: A tuple of the base-64 encoded audio URL
            and the duration of the audio.
    """
    seed_img = seed_img or "og_beat"

    seed_img_path = Path(RIFFUSION_LIB_PATH / "seed_images" / f"{seed_img}.png")
    if not seed_img_path.exists():
        seed_img_path = Path(RIFFUSION_LIB_PATH / "seed_images" / "og_beat.png")

    inputs = dacite.core.from_dict(
        InferenceInput,
        {
            "alpha": alpha,
            "num_inference_steps": 20,
            "seed_image_id": seed_img,
            "start": {
                "prompt": prompt,
                "seed": seed,
                "denoising": 0.75,
                "guidance": 7.0,
            },
            "end": {
                "prompt": prompt,
                "seed": seed + 1,
                "denoising": 0.75,
                "guidance": 7.0,
            },
        },
    )

    seed_image = Image.open(seed_img_path).convert("RGB")
    image = PIPELINE.riffuse(
        inputs,
        init_image=seed_image,
        mask_image=None,
    )
    segment = converter.audio_from_spectrogram_image(
        image,
        apply_filters=True,
    )
    mp3_bytes = io.BytesIO()
    segment.export(mp3_bytes, format="mp3")
    mp3_bytes.seek(0)

    return (
        "data:audio/mpeg;base64," + base64_util.encode(mp3_bytes),
        segment.duration_seconds,
    )
