# Inference Tools

Tools for LLM chat completion and image generation.

## chat_completion

Get LLM response via LiteLLM gateway.

```python
from hydra_tools.inference import chat_completion

# Basic usage
response = chat_completion("What is the capital of France?")

# With parameters
response = chat_completion(
    prompt="Explain quantum computing",
    model="llama-70b",
    system_prompt="You are a helpful physics teacher.",
    max_tokens=2048,
    temperature=0.7
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | str | required | The user prompt |
| `model` | str | `"llama-70b"` | Model name in LiteLLM config |
| `system_prompt` | str | None | Optional system message |
| `max_tokens` | int | 1024 | Maximum tokens to generate |
| `temperature` | float | 0.7 | Sampling temperature |

### Available Models

| Model | Backend | Best For |
|-------|---------|----------|
| `llama-70b` | TabbyAPI | Complex reasoning |
| `llama-8b` | Ollama | Fast queries |
| `qwen-7b` | Ollama | Coding tasks |
| `deepseek-coder` | TabbyAPI | Code generation |

## generate_image

Generate images using ComfyUI on hydra-compute.

```python
from hydra_tools.inference import generate_image

# Basic generation
result = generate_image("A cyberpunk cityscape at sunset")

# With full parameters
result = generate_image(
    prompt="A majestic dragon in a forest",
    negative_prompt="blurry, low quality",
    width=1024,
    height=768,
    steps=30,
    cfg_scale=7.5,
    workflow="sdxl"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | str | required | Image description |
| `negative_prompt` | str | `""` | What to avoid |
| `width` | int | 1024 | Image width |
| `height` | int | 1024 | Image height |
| `steps` | int | 20 | Sampling steps |
| `cfg_scale` | float | 7.0 | Classifier-free guidance |
| `workflow` | str | `"default"` | ComfyUI workflow name |

### Workflows

| Workflow | Description |
|----------|-------------|
| `default` | Standard SDXL generation |
| `sdxl` | SDXL with refiner |
| `lightning` | Fast 4-step generation |
| `upscale` | Image upscaling |

## embedding

Generate embeddings using Ollama.

```python
from hydra_tools.inference import embedding

# Single text
vector = embedding("Hello, world!")

# Multiple texts
vectors = embedding(["Text 1", "Text 2", "Text 3"])
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str or list | required | Text(s) to embed |
| `model` | str | `"nomic-embed-text"` | Embedding model |

## Error Handling

All tools raise `ToolError` on failure:

```python
from hydra_tools import ToolError
from hydra_tools.inference import chat_completion

try:
    response = chat_completion("Hello")
except ToolError as e:
    print(f"Error: {e}")
```

## LangChain Integration

Use as LangChain tools:

```python
from langchain.agents import initialize_agent
from hydra_tools.inference import (
    chat_completion,
    generate_image,
)

tools = [chat_completion, generate_image]
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
```
