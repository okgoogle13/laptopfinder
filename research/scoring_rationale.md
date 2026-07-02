# Scoring Rationale — Why Memory Bandwidth Over TFLOPS

## Core Finding

For **text-centric LLM inference** (the primary use case of laptopfinder), the bottleneck is **memory bandwidth**, not compute throughput (TFLOPS). This is the single most important fact that the default tech-media narrative gets wrong, and the root cause of CUDA/NVIDIA bias in hardware recommendations.

## Why Bandwidth, Not TFLOPS

During autoregressive text generation (token-by-token output), the GPU/NPU:
1. Loads model weights from memory on every forward pass
2. Performs a relatively small matrix multiply
3. Returns the result and waits for the next token

The bottleneck is step 1 — loading weights. A system with 400 GB/s but modest TFLOPS will outperform a system with massive TFLOPS but only 272 GB/s **on this workload**.

## Implication for Platform Comparison

| Platform | Bandwidth | Model Pool | Inference Verdict |
|---|---|---|---|
| M4 Max (MacBook Pro 16) | ~400 GB/s | 128GB UMA | ✅ Excellent — loads 70B Q4 at ~15–25 tok/s |
| AMD Strix Halo (64GB) | ~256 GB/s | 64–128GB UMA | ✅ Excellent — loads 70B Q4 at ~10–18 tok/s |
| RTX 4090 Laptop | ~576 GB/s | **16GB VRAM** | ⚠️ Fast but model ceiling is severe |
| RTX 4070 Laptop | ~272 GB/s | **8GB VRAM** | ❌ Cannot load 13B+ models without CPU offload |

**Key insight:** A 16GB VRAM discrete GPU cannot load a 70B Q4 model (~35GB) at all. A 64GB UMA system loads it fully, even at lower bandwidth. For the workloads laptopfinder targets, this makes UMA platforms categorically superior for models above 13B parameters.

## When CUDA IS the Right Answer

CUDA discrete GPUs are genuinely superior when the user needs:
- **Fine-tuning** (gradient computation benefits from high TFLOPS + CUDA-exclusive libs like bitsandbytes)
- **CUDA-exclusive inference kernels** (Flash Attention CUDA, vLLM CUDA, TensorRT)
- **ComfyUI + CUDA-specific custom nodes**
- **Multi-GPU inference** (not available on UMA platforms)

The laptopfinder system must **detect these signals from user input** and only then switch to the `cuda_exclusive_workload` scoring profile. It must never assume CUDA by default.

## Sources

- Alternative Silicon Hardware Dossier (Gemini Deep Research, June 2026) — `prompts/alternative_silicon_gemini.txt`
- llama.cpp benchmark threads: Apple Silicon vs Strix Halo vs CUDA
- Andrej Karpathy: "For inference on consumer hardware, memory bandwidth is the bottleneck, not FLOPS"
