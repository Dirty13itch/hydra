"""
Inference Tools for Hydra Agents

Provides LLM chat completion and image generation capabilities.
"""

import requests
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from langchain.tools import tool

from .config import get_config


@tool
def chat_completion(
    prompt: str,
    model: str = "llama-70b",
    system_prompt: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """
    Get LLM response via LiteLLM gateway.

    Args:
        prompt: User message to send
        model: Model name (llama-70b, qwen2.5-7b, qwen2.5-14b, etc.)
        system_prompt: Optional system message
        max_tokens: Maximum response tokens (default: 1024)
        temperature: Sampling temperature (default: 0.7)

    Returns:
        Model's response text
    """
    config = get_config()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        headers = {}
        if config.litellm_api_key:
            headers["Authorization"] = f"Bearer {config.litellm_api_key}"

        response = requests.post(
            f"{config.litellm_url}/v1/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        return f"Chat completion failed: {str(e)}"


@tool
def generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    cfg_scale: float = 7.0,
    workflow: str = "default",
) -> str:
    """
    Generate image using ComfyUI on hydra-compute.

    Args:
        prompt: Image description
        negative_prompt: What to avoid in the image
        width: Image width (default: 1024)
        height: Image height (default: 1024)
        steps: Sampling steps (default: 20)
        cfg_scale: Classifier-free guidance scale (default: 7.0)
        workflow: Workflow name - default, flux, sdxl (default: default)

    Returns:
        Path to generated image or error message
    """
    config = get_config()

    try:
        # Build ComfyUI workflow prompt
        workflow_data = _build_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            workflow_type=workflow,
        )

        # Queue the prompt
        response = requests.post(
            f"{config.comfyui_url}/prompt",
            json={"prompt": workflow_data},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        prompt_id = data.get("prompt_id")
        if not prompt_id:
            return "Failed to queue image generation"

        # Poll for completion
        image_path = _wait_for_completion(config.comfyui_url, prompt_id)

        if image_path:
            return f"Image generated: {image_path}"
        else:
            return "Image generation timed out or failed"

    except requests.exceptions.RequestException as e:
        return f"Image generation failed: {str(e)}"


def _build_workflow(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    cfg_scale: float,
    workflow_type: str,
) -> Dict[str, Any]:
    """Build ComfyUI workflow JSON."""

    # Basic SDXL workflow structure
    # This can be extended with more sophisticated workflows
    client_id = str(uuid.uuid4())

    if workflow_type == "flux":
        # Flux workflow (simplified)
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()),
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "flux1-dev.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["4", 1]},
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "hydra_flux", "images": ["8", 0]},
            },
        }
    else:
        # Default SDXL workflow
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()),
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["4", 1]},
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "hydra_sdxl", "images": ["8", 0]},
            },
        }


def _wait_for_completion(
    comfyui_url: str, prompt_id: str, timeout: int = 300
) -> Optional[str]:
    """Wait for ComfyUI prompt to complete and return image path."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{comfyui_url}/history/{prompt_id}",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if prompt_id in data:
                outputs = data[prompt_id].get("outputs", {})
                # Find the SaveImage node output
                for node_id, output in outputs.items():
                    if "images" in output:
                        images = output["images"]
                        if images:
                            filename = images[0].get("filename", "")
                            subfolder = images[0].get("subfolder", "")
                            if filename:
                                return f"{subfolder}/{filename}" if subfolder else filename

            time.sleep(2)

        except requests.exceptions.RequestException:
            time.sleep(2)
            continue

    return None


def list_models() -> Dict[str, List[str]]:
    """
    List available models from all inference backends.

    Returns:
        Dict with models grouped by backend
    """
    config = get_config()
    models = {"tabbyapi": [], "ollama": [], "litellm": []}

    # TabbyAPI models
    try:
        response = requests.get(f"{config.tabbyapi_url}/v1/models", timeout=10)
        if response.ok:
            data = response.json()
            models["tabbyapi"] = [m["id"] for m in data.get("data", [])]
    except requests.exceptions.RequestException:
        pass

    # Ollama models
    try:
        response = requests.get(f"{config.ollama_url}/api/tags", timeout=10)
        if response.ok:
            data = response.json()
            models["ollama"] = [m["name"] for m in data.get("models", [])]
    except requests.exceptions.RequestException:
        pass

    # LiteLLM models (virtual routes)
    try:
        headers = {}
        if config.litellm_api_key:
            headers["Authorization"] = f"Bearer {config.litellm_api_key}"
        response = requests.get(
            f"{config.litellm_url}/v1/models",
            headers=headers,
            timeout=10,
        )
        if response.ok:
            data = response.json()
            models["litellm"] = [m["id"] for m in data.get("data", [])]
    except requests.exceptions.RequestException:
        pass

    return models


def get_model_info(model: str = None) -> Dict[str, Any]:
    """
    Get information about currently loaded model(s).

    Args:
        model: Optional specific model to query

    Returns:
        Dict with model information
    """
    config = get_config()
    info = {}

    # TabbyAPI current model
    try:
        response = requests.get(f"{config.tabbyapi_url}/v1/model", timeout=10)
        if response.ok:
            info["tabbyapi"] = response.json()
    except requests.exceptions.RequestException:
        info["tabbyapi"] = {"error": "unreachable"}

    # Ollama running models
    try:
        response = requests.get(f"{config.ollama_url}/api/ps", timeout=10)
        if response.ok:
            info["ollama"] = response.json()
    except requests.exceptions.RequestException:
        info["ollama"] = {"error": "unreachable"}

    return info
