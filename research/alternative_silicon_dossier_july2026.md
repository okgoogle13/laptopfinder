# Alternative Silicon Dossier - July 2026

This is the canonical research artifact for the alternative-silicon workstream. It consolidates the July 2026 market findings and preserves the few June observations that were not duplicated in the downstream prompts and docs.

## Executive Summary

For text-centric local LLM inference, Apple Silicon UMA and AMD Strix Halo remain the primary alternative-silicon paths. They are the systems to prioritize when the buyer wants portable, low-noise, sustained interactive use without defaulting to CUDA hardware.

Desktop Mac Studio systems, mini-PCs, and eGPU bundles still matter, but only as secondary comparators. They are useful when they sharpen the price/performance story or expose a better landed-cost option, not because they are the default form factor.

Discrete mobile GPUs remain relevant for buyers who need CUDA- or ROCm-adjacent flexibility, but the center of gravity for the July 2026 advice is still mobile-first: laptop and fieldable workstation chassis before desktop substitutes.

## Canonical Procurement Takeaways

- Apple Silicon UMA is the cleanest buyer experience for local inference.
- Strix Halo is viable when the buyer values system memory capacity and form factor flexibility over raw memory bandwidth.
- Radeon mobile GPUs are a buyer-disclosure path rather than a disqualifying one.
- eGPU systems are a secondary route and should be treated as a portability compromise, not a first-choice recommendation.

## Legacy Comparator Guidance

Mac Studio M1 Max and M2 Max systems remain useful comparator systems, especially when a seller is trying to price a portable MacBook Pro against a desktop chassis on the same silicon. The portable machine should generally win the buyer-facing framing unless the desktop is materially cheaper per usable GB of unified memory.

Desktop Apple Silicon also remains a valid benchmark for capacity-heavy comparisons, but not because the desktop form factor is preferred. It is retained because it is a useful ceiling reference for unified-memory pricing.

## June Observations Retained

- The DRAM shortage continued to lift the used-price floor for higher-memory Apple Silicon systems, especially 96 GB and 128 GB configurations.
- Mac Studio M1 Max 64 GB and M2 Max 96 GB were among the strongest repeatable reference points in the June material.
- Mid-range RTX 4090 and RTX A5000-class laptops remained relevant comparator targets for buyers who still want discrete mobile GPUs rather than UMA systems.
- The ASUS ROG Ally X 24 GB remained below the UMA shortlist gate and is therefore best treated as an edge case, not a target.

## Scoring Context

The UMA score ceiling is still removed. Apple Silicon and Strix Halo compete on the full 0-100 `llm_index_score` scale, and the decision engine should not reintroduce a ceiling in prose or guidance.

The live threshold references still live in the SRL and the repo rules:

- UMA shortlist gate: 32 GB
- Discrete standard mobile VRAM gate: 16 GB
- Touchscreen exception: 12 GB minimum only when the listing explicitly confirms a digitizer

## Maintenance Note

The raw Gemini and Perplexity outputs that informed this dossier live under `research/archive/`. This file is the human-readable consolidation layer for downstream prompts and operator guidance.
