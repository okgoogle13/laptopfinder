# Bias Guard — Pre-Recommendation Self-Check

Apply this check before finalising any hardware shortlist or recommendation.

## Step 1: Identify the Workload

If the workload is any of: **chat, agents, coding assist, RAG, document analysis, local LLM hosting** → proceed to Step 2.

If the workload is explicitly training, fine-tuning, or diffusion → skip Steps 2–3 (CUDA is appropriate; no note required).

## Step 2: Assert UMA Representation

Check the shortlist for:
- At least one **Apple UMA** candidate (Apple Silicon Max/Ultra, ≥64GB unified memory)
- At least one **Strix UMA** candidate (AMD Ryzen AI Max / Strix Halo, ≥64GB unified memory)

If either is missing, add representative candidates before continuing.

## Step 3: Justify Any CUDA/ROCm Inclusion

If a discrete CUDA or ROCm device appears in the shortlist for a text-centric workload, include a **Bias Guard Note** in the recommendation body:

> **Bias Guard Note:** This discrete GPU recommendation is included because [specific technical reason — e.g. "the user requires CUDA-locked inference stack X" / "no UMA hardware is available in this price range on AU used market"]. Apple Silicon UMA and Strix Halo UMA were evaluated and [reason for exclusion — e.g. "exceed budget" / "insufficient AU listings"]. If those constraints are relaxed, UMA alternatives should be preferred for this workload.

If no justification can be written, remove the CUDA/ROCm entry and replace with a UMA alternative.
