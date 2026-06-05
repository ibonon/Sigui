import modal
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Create the Modal App
app = modal.App("imina-na-v2-serve")

# Define the image:
# We need vLLM, huggingface_hub, and the dependencies for Qwen2-VL.
# Flash Attention is highly recommended for performance.
vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm==0.5.4",
        "huggingface_hub",
        "qwen-vl-utils",
        "transformers",
        "accelerate",
    )
    # Authenticate with HuggingFace if accessing private/gated models (Optional but good practice)
    # .env({"HF_TOKEN": "your_hf_token_here"}) 
)

# 1. Define the deployment model and configuration
MODEL_NAME = "Ibonon/Imina-Na-V2" # Assuming you've uploaded it here!

# For Qwen2-VL-7B-Instruct with LoRA, it's generally best to load the base model 
# and the LoRA adapter if using standard transformers, but vLLM has specific LoRA support.
# If you uploaded a MERGED model to Ibonon/Imina-Na-V2, it's much easier for vLLM.
# Assuming Ibonon/Imina-Na-V2 is a merged model or a base model that vLLM can load directly.

class VisionRequest(BaseModel):
    action: Dict[str, Any]
    graph: Optional[Dict[str, Any]] = None

# 2. Define the Inference Engine
@app.cls(
    image=vllm_image,
    gpu="A10G",          # A10G (24GB VRAM) is sufficient for 7B at fp16/bf16 with vLLM
    scaledown_window=300, # Keep container alive for 5 minutes after last request to avoid cold starts
    min_containers=0,         # Set to 1 if you want to pay to keep 1 instance running 24/7 (Warning: ~$1.30/hr!)
)
class IminaNaVLLMEngine:
    @modal.enter()
    def setup(self):
        """Loads the model into VRAM when the container starts."""
        from vllm import LLM
        
        print(f"Loading {MODEL_NAME} into vLLM...")
        # Note: If your model requires specific vLLM trust_remote_code, enable it.
        # Max model len might need tuning based on your graph input size.
        self.llm = LLM(
            model=MODEL_NAME,
            trust_remote_code=True,
            max_model_len=4096, 
            gpu_memory_utilization=0.9,
            # enforce_eager=True # Sometimes needed if CUDA graph issues occur
        )
        print("Model loaded successfully!")

    @modal.method()
    def infer(self, messages: list[dict], temperature: float = 0.0) -> str:
        """Standard inference method."""
        from vllm import SamplingParams
        
        # We need to format the chat messages for Qwen2-VL
        # For simplicity in this demo endpoint, we assume the prompt is correctly formatted
        # or we rely on vLLM's built-in chat template if it supports it for Qwen-VL.
        
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=256, # JSON response shouldn't be long
            # stop=["<|im_end|>"] # Adjust based on Qwen's specific stop tokens if needed
        )
        
        # If using standard chat templates:
        prompt = ""
        for msg in messages:
            prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        outputs = self.llm.generate([prompt], sampling_params)
        return outputs[0].outputs[0].text

# 3. Define the FastAPI/Web Endpoint
@app.function(image=vllm_image)
@modal.fastapi_endpoint(method="POST")
def evaluate(request: Dict):
    """
    HTTP Endpoint matching the format expected by Sigui's imina_na_vision.py
    
    Expected input format matches the OpenAI Chat Completions API roughly:
    {
        "model": "Ibonon/Imina-Na-V2",
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ]
    }
    """
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.0)
    
    # Call the GPU engine
    engine = IminaNaVLLMEngine()
    result_text = engine.infer.remote(messages, temperature)
    
    # Format the response to match what httpx expects in imina_na_vision.py
    return {
        "id": "modal-imina-na-v2",
        "object": "chat.completion",
        "model": request.get("model", MODEL_NAME),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result_text
                },
                "finish_reason": "stop"
            }
        ]
    }

# 4. Entrypoint for testing locally
@app.local_entrypoint()
def test_local():
    print("Testing the deployment...")
    engine = IminaNaVLLMEngine()
    
    test_messages = [
        {
            "role": "system",
            "content": "You are Imina Na. Return valid JSON only with keys: pattern, confidence, risk_delta, visual_evidence, model."
        },
        {
            "role": "user",
            "content": "Infer blockchain graph risk signal from this action and graph payload.\nAction: {'amount_usdc': 1500, 'destination': '0xBad'}\nGraphSummary: {'focus_tx_count': 10, 'focus_unique_peer_senders': 5}"
        }
    ]
    
    result = engine.infer.remote(test_messages, temperature=0.0)
    print(f"Result:\n{result}")

"""
HOW TO DEPLOY:
1. Ensure your model is uploaded to HuggingFace at 'Ibonon/Imina-Na-V2'.
   (Ideally, a merged weights version for easiest vLLM loading).
2. Run: `modal setup` (if you haven't authenticated)
3. Run: `modal deploy serve_imina_na.py`

Modal will give you a URL like:
https://<your-username>--imina-na-v2-serve-evaluate.modal.run

You can then put this URL directly into your Sigui `.env`:
VISION_ENDPOINT=https://<your-username>--imina-na-v2-serve-evaluate.modal.run
"""
