# System Context — LaptopFinder Inference Planner

## Purpose

Local, text-centric LLM inference planning for AU hardware procurement. Goal: identify hardware that runs large models (≥13B parameters) entirely in memory, with low noise, low power, and sustainable thermals for sustained interactive use.

## Paradigm Priority

Treat **Apple Silicon UMA** and **AMD Strix Halo UMA** as first-class paradigms. These architectures eliminate the PCIe bandwidth bottleneck by sharing a unified memory pool between CPU and GPU. For text-only workloads (chat, agents, coding assist, RAG, document analysis), unified memory enables larger context windows and larger model files than any discrete GPU at the same price point.

Do **not** default to CUDA/NVIDIA unless:
- The workload requires training, fine-tuning, or diffusion inference
- The software stack is hard-locked to CUDA (e.g. TensorRT-LLM, NeMo)
- The user explicitly requests CUDA hardware

## Shortlist Requirements for Text-Centric Workloads

Any shortlist produced for text-centric inference must include:
- ≥1 Apple Silicon UMA candidate (Mac Studio or MacBook Pro M-series, ≥64GB)
- ≥1 AMD Strix Halo UMA candidate (GMKtec EVO-X2, Minisforum UM890 XTX, ASUS ROG Ally X, or equivalent)

If neither category is represented, the shortlist is incomplete.

## Reference Material

Ground recommendations in:
- `research/alternative_silicon_dossier_june2026.md` — synthesised market and technical findings
- `config/silicon_profiles.yaml` — paradigm definitions and workload preferences
- `config/scoring_weights.yaml` — per-workload scoring weight profiles
- `data/hardware_taxonomy.json` — representative hardware entries by paradigm
