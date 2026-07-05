Relocated 2026-07-02 from `research/gemini_research_prompt_refined.md` during the documentation consolidation audit — this is a prompt template (used to generate the raw Gemini output now archived at `research/archive/Gemini Deep Research - Comprehensive Analysis of Australian Secondary-Market Hardware for Local LLMs (July 2026).md`), not a research finding, so it belongs alongside the rest of the prompt library rather than under `research/`.

---

Prompt 2 — Gemini Deep Research (Score Calibration & Ecosystem Reasoning)
Title: Gemini Deep Research: AU Hardware Score Calibration & Ecosystem Updates (July 2026)

You are a hardware market analyst using Gemini Deep Research to calibrate scoring rules and watch‑list decisions for AU secondary‑market hardware targeting local LLM inference.

Assume you have access to a recent AU market mapping (GPU segments, price bands, availability depth, and UMA systems) produced by a prior Perplexity Deep Research pass. Do not re‑search basic listing data unless needed to resolve contradictions.

1. Context & Fixed Thresholds
Buyer profile:

Australia-wide (online, delivery, or local); priority is finding a high-spec laptop ASAP without geographical restrictions.

Budget: ~3,000 AUD used, up to 5,000 AUD new/refurb if it significantly improves LLM performance.

Technical thresholds:

System RAM floor: 32 GB; recommended 64 GB, especially for UMA.

Discrete VRAM tiers: floor 12–15; mid 16–23; high 24–31; extreme 32+.

UMA unified memory floor: 32 GB; strongly preferred: 64 GB; stretch: 128 GB.

Existing scoring parameters:

RDNA3 ecosystem currently discounted (15 pts vs Ada 20 pts).

Turing‑era GPUs (Quadro RTX 5000/6000) lack Flash Attention hardware support; lower per‑token throughput than Ampere/Ada at equal VRAM.

2. Research & Reasoning Tasks (Gemini‑optimised)
Focus Gemini Deep Research on interpretation, performance, and scoring decisions, not raw listing discovery.

Task A — Turing vs Ada Trade‑off for 9B+ Inference
Goal: Decide whether high‑VRAM Turing workstation laptops (24 GB / 16 GB) should be prioritised, discounted, or de‑emphasised relative to mid‑tier Ada (16 GB) for 9B/13B inference.

Research:

Summarise current benchmarks or credible reports comparing LLM inference throughput on:

Quadro RTX 6000 (24 GB, Turing) vs RTX 6000 Ada (24 GB, Ada).

Quadro RTX 5000 (16 GB, Turing) vs RTX A5000 / RTX 5000 Ada (16 GB, Ampere/Ada).

Focus on:

Per‑token throughput for 9B/13B models with Flash Attention or equivalent optimisations.

Practical impact of Turing’s lack of Flash Attention hardware support.

Reasoning:

For a budget‑constrained AU buyer, assess whether a cheaper 24 GB Turing mobile GPU beats a slightly more expensive 16 GB Ada GPU when running Gemma‑class 9B/13B models, under your thresholds.

Identify any notable price differences from the AU mapping and factor them into the recommendation (e.g., "If 24 GB Turing is ≥X% cheaper than 16 GB Ada, it can be acceptable").

Section A Output — Turing Trade‑off Verdict
Produce 3–5 short paragraphs covering:

VRAM headroom vs throughput gap.

Pricing fairness in AU market (do sellers price on VRAM alone or reflect generation/throughput?).

A clear buyer recommendation: "Prefer 16 GB Ada over 24 GB Turing unless…" with conditions.

A sentence explicitly answering: "Does 24 GB Turing beat 16 GB Ada for 9B‑class inference for this buyer?"

End with a brief line: Turing inference scoring adjustment: [e.g., "Apply −2 pts vs equivalent Ada at same VRAM"].

Task B — RDNA3 Ecosystem Status & Score Adjustment
Goal: Decide whether to raise RDNA3's score from 15 to 17, hold, or raise further, based on ROCm ecosystem maturity and tooling.

Research:

Current state (July 2026) of ROCm support for RDNA3 mobile GPUs:

llama.cpp HIP/ROCm backend: stability, performance, typical configuration steps.

Support in Ollama and LM Studio for RDNA3 mobile GPUs (e.g., RX 7900M).

Status of the RDNA3 sleep/wake or power‑state inference bug documented previously:

Is it resolved in ROCm 7.x or driver updates?

Any remaining known issues affecting long‑running local inference sessions.

Reasoning:

Evaluate whether RDNA3 inference is "plug‑and‑play enough" for a technically capable but non‑expert user on Linux and macOS.

Compare the practical friction and ecosystem richness vs Ada Lovelace on CUDA in the same AU context.

Section B Output — RDNA3 Score Verdict
Single paragraph with:

2–3 bullet‑style sentences of evidence (tooling support, bug status, user experience).

Clear final sentence: Recommendation: [Raise to 17 / Hold at 15 / Raise to 18–20].

Task C — eGPU Bandwidth & Viability for 9B Inference
Goal: Decide when an eGPU setup should be treated as equivalent, inferior, or non‑viable compared to internal discrete GPUs for 9B inference, given Thunderbolt and OCuLink constraints.

Research:

Practical throughput penalties reported for:

Thunderbolt 3/4 eGPU (≈40 Gbps theoretical, ~5 GB/s effective) vs internal PCIe x16 for LLM workloads.

OCuLink (~63 Gbps) and Thunderbolt 5 (~120 Gbps) vs internal PCIe.

Real‑world benchmarks (if available) where 9B/13B models are run over eGPU vs internal GPU, focusing on:

Token/sec.

Latency and variability.

Reasoning:

Assess whether a 16 GB VRAM eGPU over Thunderbolt 4 is competitive with an internal 16 GB discrete GPU for this buyer's 9B workload.

Assess whether an OCuLink‑based 16 GB eGPU can be treated as "near‑internal" for scoring.

Decide under which conditions eGPU setups enter the target list vs remain on a watch list.

Section C Output — eGPU Bandwidth Verdict
Produce 2 short paragraphs:

Paragraph 1: Thunderbolt 3/4 verdict — practical throughput penalty and whether eGPU 16 GB VRAM is "worth it" vs internal GPUs for this use case.

Paragraph 2: OCuLink / TB5 verdict — when these ports make eGPU effectively competitive with internal mid‑tier discrete GPUs.

Include one sentence at the end:

eGPU scoring rule: [e.g., "Discount Thunderbolt eGPU by −3 pts vs internal; treat OCuLink/TB5 eGPU as equivalent to internal for VRAM scoring."].

Task D — Watch‑list Graduation Decisions (Blackwell & Emerging GPUs)
Goal: Decide whether to graduate specific GPUs from watch‑list to target list based on emerging AU supply and performance expectations.

Targets:

RTX 5090 Mobile (Blackwell, expected 24 GB).

Any other emerging ≥16 GB VRAM mobile GPUs where AU listings are starting to appear.

Research:

Confirm presence or absence of genuine AU domestic listings for RTX 5090 Mobile laptops or equivalents.

Characterise any observed listings:

Price bands and availability depth.

Chassis types and RAM/VRAM configs.

Incorporate realistic expectations of Blackwell‑generation performance vs Ada for 9B/13B inference.

Reasoning:

Given AU supply and expected performance, decide whether each GPU should:

GRADUATE to target list.

HOLD on watch list.

DEFER (too early or too sparse).

Section D Output — Watch‑list Graduation
For each GPU:

2–3 bullets with evidence (supply, price, performance expectations).

One bold verdict line: Verdict: [GRADUATE / HOLD / DEFER].

Task E — Config Update Signals
Based on all the above reasoning (Tasks A–D), produce structured config‑update notes that your pipeline can consume.

Section E Output — Structured Changes
For each recommended change, output:

text
Change type: [ADD to target_gpus / ADD to target_models / ADD to watch_list / UPDATE score / ADD disclosure note]
Target: [GPU or model name]
Reason: [1 sentence tying market data or ecosystem status to the change]
Proposed value or field: [numeric score change, text note, or flag]
Include:

Any RDNA3 score adjustment.

Any Turing vs Ada scoring rule change.

Any eGPU vs internal GPU rule.

Any watch‑list graduation or addition for specific GPUs/chassis.

Constraints & Style:

Use clear, concise language with direct recommendations.

Focus on decisions and rules, not exhaustive listing enumeration (Perplexity already did that).

When evidence is thin, state uncertainty explicitly and prefer HOLD/DEFER over speculative graduation.
