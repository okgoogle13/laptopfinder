Relocated 2026-07-02 from `research/perplexity_research_prompt_refined.md` during the documentation consolidation audit — this is a prompt template (used to generate the raw Perplexity output now archived at `research/archive/Perplexity Deep Research  AU Secondary Laptop & eGPU Market Mapping for Local LLMs (July 2026).md`), not a research finding, so it belongs alongside the rest of the prompt library rather than under `research/`.

---

Prompt 1 — Perplexity Deep Research (AU Laptop & eGPU Market Mapping)
Title: Perplexity Deep Research: AU Secondary Laptop & eGPU Market Mapping for Local LLMs (July 2026)

You are an evidence‑driven hardware market analyst using Perplexity Deep Research to map the Australian secondary‑market supply of high‑VRAM laptops and eGPU setups for local LLM inference.

1. Buyer & Scope Context
Location: Australia-wide (online, delivery, or local); priority is finding a high-spec laptop ASAP without geographical restrictions.

Budget: ~3,000 AUD for used; up to 5,000 AUD for new or refurbished if it materially improves local LLM capability.

Platforms to search:

Primary: eBay AU (domestic listings), Facebook Marketplace (Australia-wide), Gumtree.

Secondary: eBay global "ships to AU" — record separately, never fold into AU domestic price bands.

Use case: Running Gemma‑class 9B local LLM inference alongside Antigravity IDE, browser, Claude Code CLI, and Google Drive sync.

2. Fixed Technical Thresholds (Reference Only)
Treat these thresholds as fixed context when judging suitability; do not attempt to re‑derive them.

System RAM (discrete laptops): floor 32 GB; recommended 48–64 GB; stretch 96 GB.

System RAM (UMA laptops/mini‑PCs): floor 32 GB; recommended 64 GB; stretch 96 GB.

Discrete VRAM tiers:

Floor: 12–15 GB (operational minimum for 9B).

Mid: 16–23 GB (preferred for 9B+/13B).

High: 24–31 GB (enables 30B Q4).

Extreme: 32+ GB (enables 70B Q4).

UMA unified memory: floor 32 GB; strongly preferred 64 GB; stretch 128 GB.

When giving verdicts, always reference these tiers (floor/mid/high/extreme) and RAM floors.

3. Research Tasks (Perplexity‑optimised)
Focus Perplexity Deep Research on current AU listings and concrete price/availability mapping.

Task A — Discrete GPU Laptop Supply (AU Used / New)
For each of the following GPU segments, map AU domestic listings (plus a separate note for "ships to AU") as of July 2026:

Ada gaming laptops (high VRAM)

Focus GPUs: RTX 4090 Mobile (16 GB), RTX 5080 Mobile (16 GB).

Questions:

Which chassis lines appear (e.g., Razer Blade 18, ASUS ROG, GIGABYTE AORUS 17/18) with these GPUs?

Typical AU used price bands: sub‑3,500 AUD, 3,500–5,000 AUD, above 5,000 AUD.

Availability depth: common / moderate / rare / isolated.

Typical RAM configurations (note any ≥32 GB and ≥64 GB).

Ada "floor tier" laptops (12–15 GB VRAM)

Focus GPUs: RTX 4080 Mobile (12 GB), RTX A3000 (12 GB), any 12–15 GB Ampere mobile GPUs that appear domestically.

Questions:

Which chassis lines carry these GPUs (gaming, workstation, touchscreen)?

AU used price bands and availability depth.

Confirm whether VRAM sits in floor tier (12–15 GB) and record RAM configs.

Workstation Ada/Ampere (mid/high VRAM)

Focus GPUs: RTX A4500 (16 GB), RTX A5000 (16 GB), RTX A5500 (16 GB), RTX 5000 Ada (16 GB), RTX 6000 Ada (24 GB).

Questions:

Typical chassis: HP ZBook Fury, Lenovo ThinkPad P16, Dell Precision 7680, ASUS ProArt Studio, others.

Typical AU used/refurb price ranges (domestic only) and seller types (enterprise off‑lease, corporate reseller, private).

Availability depth and RAM/VRAM tiers (floor/mid/high).

Turing‑era workstation laptops

Focus GPUs: Quadro RTX 6000 (24 GB), Quadro RTX 5000 (16 GB).

Questions:

Are AU domestic listings present? Which platforms and chassis (ZBook, ThinkPad P, Precision)?

Typical price bands (sub‑3,000, 3,000–4,000, above 4,000 AUD).

Availability depth and whether sellers emphasise VRAM or generation in descriptions.

For all segments, explicitly separate:

Domestic AU listings (AU‑based seller or shipping).

Overseas listings that "ship to AU" (note country and shipping cost if visible).

Section A Output — Discrete GPU Overview Tables
Produce three markdown tables, one per VRAM tier:

Floor tier (12–15 GB)

Mid tier (16–23 GB)

High/extreme tier (24+ GB)

Each table row:

GPU Model | Generation | VRAM GB | Typical Chassis Lines | AU Used Price Band (domestic) | Overseas Price Band ("ships to AU") | Availability Depth | Typical RAM | Suitability Verdict for 9B

Keep verdict to a short phrase (e.g., "viable but tight KV cache", "strong 9B/13B host").

Task B — eGPU Enclosure & Host Market (AU)
Use Deep Research to identify actual AU listings and pricing.

eGPU enclosures:

Focus: ROG XG Mobile, Razer Core X / Core, generic Thunderbolt 3/4 eGPU boxes.

Questions:

Which models appear on eBay AU / Gumtree / FB Marketplace?

Typical AU prices for enclosure only and for bundle (enclosure + GPU).

Typical GPUs inside bundles (model + VRAM).

eGPU host laptops:

Identify laptop models commonly listed with eGPU enclosures (bundles).

Note:

Host RAM and internal GPU (if any).

Whether the listing markets LLM, AI, or "creator" workloads.

OCuLink / Thunderbolt 5 hosts:

Identify compact laptops or mini‑PCs available domestically with:

OCuLink ports marketed for external GPUs, or

Thunderbolt 5 ports with explicit GPU expansion marketing.

Record AU prices for host only, without GPU, focusing on sub‑3,000 AUD.

Section B Output — eGPU Market Tables & Notes
Table B1 (Enclosures & Bundles): Enclosure Model | Typical GPU Inside | VRAM GB | AU Price Range (domestic) | Availability Depth | Seller Type | Notes

Table B2 (Hosts with eGPU / OCuLink / TB5): Host Model | Port Type (TB3/TB4/TB5/OCuLink) | RAM | Internal GPU | AU Price (host only) | Bundle Price (if any) | Availability Depth | Notes

Short bullet list afterwards:

3–5 bullets summarising which eGPU setups look practically buyable within budget vs theoretical only.

Task C — UMA Gap Systems (Non‑Apple)
Focus on unified‑memory systems not covered in earlier runs.

Targets:

ASUS ProArt Studio 16 (Strix Halo or similar high‑UMA configs).

Framework 16 (AMD) with and without discrete modules.

Mac Mini M4 Pro and M4 Max (24–64 GB unified memory).

Questions per model line:

Are AU domestic used/new/refurb listings visible?

Typical unified memory / RAM configurations (highlight ≥64 GB).

AU price bands (domestic only) vs "ships to AU".

Availability depth and notable constraints (e.g., "import‑only from US Apple Store").

Section C Output — UMA Gap Table
Single table:

Model | Unified Memory / RAM | Internal GPU / APU | AU Price Band (domestic) | Overseas Import Price Band | Availability Depth | vs Mac Studio M1 Max 64 GB Price | Shortlist Verdict (Yes/No + brief reason)

Task D — Discovery Keywords
Based on what you find, output 5–10 ready‑to‑paste eBay AU search strings that surface relevant high‑VRAM and UMA listings which might be missed by naive searches.

Section D Output: bullet list of search strings (no commentary).

Quality constraints:

Always cite sources and make price bands and availability judgments traceable to actual AU listings.

If AU data is thin or absent for any segment, say "Sparse AU data" and give a qualitative note instead of inventing a price band.

Do not restate prior Apple Silicon/Strix Halo pricing; focus only on new or updated segments.
