# Alternative Silicon Dossier — June 2026

*Synthesised from deep_research_output.md (Gemini) and perplexity-research-report.md (Perplexity). AU market, Northcote VIC buyer, ≤5,000 AUD.*

---

## Executive Summary

For text-centric LLM inference, **Apple Silicon UMA** is the mature benchmark and **AMD Strix Halo UMA** is the emergent x86 alternative. Both provide unified memory that eliminates the PCIe bottleneck, enabling models larger than any discrete mobile GPU can hold. Discrete CUDA/ROCm hardware should be treated as secondary for this workload — capable, but architecturally constrained to discrete VRAM capacity.

RTX 5080/5090 mobile GPUs remain watch-list only (halo-tier pricing, sparse AU availability as of mid-2026). The strongest repeatable targets within AUD 3–5k are M1/M2 Max Apple Silicon desktops and mid-range RTX 4090/A5000 laptops.

---

## Apple Silicon UMA

### Why It Wins for Text Inference

Apple Silicon UMA is the most mature ecosystem for local LLM inference. The Metal backend in `llama.cpp` and the MLX framework are production-grade. Unified memory removes the PCIe bottleneck: the full RAM pool is the GPU VRAM budget, so a 64 GB M1 Max can run a 70B Q4 model at >10 tok/s — impossible on any 16 GB discrete VRAM device.

### AU Used Market (June 2026)

| Configuration | Typical AU Used Price | Availability |
|:---|:---|:---|
| Mac Studio M1 Max 64GB | $2,600–$3,200 | Moderate |
| Mac Studio M2 Max 96GB | $3,800–$4,800 | Rare |
| MacBook Pro 16" M1 Max 64GB | $2,500–$3,500 | Common |
| MacBook Pro 16" M2 Max 96/128GB | $4,500–$6,000 | Rare |
| MacBook Pro 16" M3 Max 128GB | $5,500–$7,000 | Low |

**DRAM shortage impact:** As of mid-2026, sellers are increasingly pricing high-RAM (96/128 GB) Apple Silicon units at a significant premium, aware of their "LLM-workstation" utility. This raises the floor for these tiers compared to base-model units.

### Pipeline Scoring Note

The 75-point UMA score ceiling in `config/static_reference_layer.json` has been removed as of 2026-06-30. Apple Silicon UMA platforms now compete at the full 0–100 `llm_index_score` scale alongside discrete GPU laptops. A Mac Studio M1 Max 64GB with low risk and a strong seller now scores ~89, reflecting its genuine inference capability advantage.

---

## AMD Strix Halo UMA

### Platform Status

Strix Halo (Ryzen AI Max / Ryzen AI Max+) is the emergent x86 UMA competitor. Key specs:
- Up to 256 GB LPDDR5x unified memory (current AU units: 64/128 GB)
- ~215 GB/s peak memory bandwidth (vs ~400 GB/s on M1 Max)
- ROCm/Vulkan/llama.cpp+Vulkan inference support — functional but less plug-and-play than macOS

### AU Market Availability

Units appear primarily as imports or via specialist retailers. Common SKUs:
- **GMKtec EVO-X2** (Ryzen AI Max+ 395) — most frequently listed, often mislabeled as "ROG NUC" or "Ryzen AI Mini PC"
- **Minisforum UM890 XTX** — alternate Strix Halo mini-PC
- **ASUS ROG Ally X** — handheld form factor, 24 GB unified memory (below 64 GB threshold for shortlist)

Landed cost for 64 GB configs: AUD $2,800–$4,000 depending on storage.

### Inference Readiness

Community testing (lhl/strix-halo-testing, June 2026) confirms Strix Halo is functional for inference at 215 GB/s but requires more setup than Apple Silicon. ROCm/Vulkan toolchains are under active development. Not recommended as a "plug-and-play" platform for non-technical users.

---

## Discrete CUDA (NVIDIA Mobile)

Relevant for training, diffusion, or CUDA-locked software stacks. Not the recommended paradigm for text-centric inference — VRAM cap (typically 16 GB on mobile) is the hard limit.

### Active Targets (AU Used)

| GPU | VRAM | Typical AU Used | Notes |
|:---|:---|:---|:---|
| RTX 4090 (mobile) | 16 GB | $3,500–$5,000 | Strong generation; limited AU supply |
| RTX 3080 Ti (mobile) | 16 GB | $2,200–$3,000 | Common; mature used market |
| RTX A5000 (mobile) | 16 GB | $2,500–$3,500 | Workstation; ECC, ISV drivers |
| RTX A5500 (mobile) | 16 GB | $3,000–$4,500 | Ada-gen workstation; emerging used supply |

### Watch-List Only (Not Yet Ready)

- **RTX 5080/5090 (mobile):** Halo-tier pricing, no meaningful AU used supply as of mid-2026. Keep as watch-list. Revisit Q3 2026.
- **RTX 5000 Ada (mobile, workstation):** Pre-order phase in AU. Realistically above 5k AUD new; sparse used supply.

---

## Discrete ROCm (AMD Mobile)

### RX 7900M — Current Target

16 GB GDDR6, ~576 GB/s theoretical bandwidth. Appears in:
- ASUS ROG Strix SCAR 18
- MSI Titan 18

ROCm/Vulkan support is improving. Not a penalty in the pipeline — evaluated at the same risk gate as CUDA GPUs, with a buyer disclosure note surfaced. Bandwidth advantage over CUDA mobile (576 vs ~400 GB/s) is offset by ecosystem maturity gap and smaller driver/toolchain community.

---

## Missing Targets (from Perplexity Research)

The following GPU families meet the ≥16 GB VRAM threshold but are absent from current `target_gpus`:

1. **RTX A5500 (mobile)** — Ada workstation, 16 GB, Dell Precision/ZBook Fury class. Entering secondary market via corporate off-lease.
2. **Quadro RTX 6000 (mobile)** — Legacy, 24 GB VRAM. Heavily discounted vs Ada. Potential undervalued pick in Ampere-era mobile workstations.
3. **Quadro RTX 5000 (mobile)** — Legacy, 16 GB. Off-lease ThinkPad P-series.

Laptop model families worth adding to `target_models`:
- Dell Precision 7680 / 5690 (RTX 5000 Ada / A-series configs, ≥16 GB)
- HP ZBook Fury 16 G10/G11 (RTX A-series)

---

## Scoring and Pipeline Implications

### UMA Ceiling Removal

Prior to 2026-06-30, `apple_silicon.score_ceiling: 75` capped all UMA platform scores in `llm_index_score`. This ceiling has been **removed**. UMA platforms now compete at full 0–100 scale, reflecting:
- Higher inference throughput per dollar for text workloads
- Larger effective context window (entire system RAM available as model buffer)
- Quieter thermals for sustained interactive use

### RDNA3 Score Rationale

`gpu_generation_points` scores RDNA3 at 15 vs Ada at 20. This is a **software ecosystem maturity discount** (ROCm/Vulkan toolchain friction), not a performance ceiling. Revisit as ROCm matures — potentially raise to 17–18 by Q4 2026 if Vulkan/ROCm parity improves.

### target_gpus Scope

`target_gpus` in the SRL is scoped to **training/diffusion/CUDA workloads**. It is not used for text-centric inference ranking, which uses `score_text_llm_candidate()` with `scoring_weights.yaml` profiles instead.
