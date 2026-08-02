I don’t have live access to current AU stock and detailed SKU-by-SKU specs right now. I can outline a targeted checklist and what to look for so you can verify quickly, then we can proceed if you want me to fetch updates once tools are available.

What to verify for each model
- Exact SKU and generation identifier
  - Record the precise model code (e.g., Strix Halo Ryzen AI Max 395) and Australian generation suffix (e.g., GA605 for a specific Zephyrus G16 variant).
- RAM config
  - Total system memory and DIMM type (LPDDR5X soldered on-board vs SO-DIMM, e.g., LPDDR5X-8533).
  - Note whether the 32GB+ RAM figure is soldered or upgradeable, and if there are multiple SKUs with different RAM amounts.
- GPU/iGPU details
  - GPU model name (e.g., RDNA 3.5-based iGPU in Strix Halo) and its VRAM/shared memory mechanics.
  - Confirm the maximum GPU-addressable memory allocation (e.g., up to 96GB unified memory or other), and flag if unconfirmed by manufacturer.
  - Clarify any confusion between “RAM” and “VRAM” in listings (16GB RAM being mistaken for GPU memory).
- LLM inference stack status
  - AMD: ROCm support status for the integrated GPU or Vulkan kernel status; note any limitations for llama.cpp or similar.
  - Intel: oneAPI/SYCL/OpenVINO support status for unified-memory GPUs; note current compatibility with local LLM inference.
- Australian price and stock
  - New retail price from Lenovo AU, JB Hi-Fi, Umart, Scorptec, Centre Com, or eBay AU where applicable.
  - Used/refurbished prices from ebay.com.au as available.
  - Stock status: in stock, pre-order, backorder, or unavailable in AU as of July 2026.
- Flagging potential ambiguities
  - Explicitly flag any listing where 16GB RAM could be mistaken for GPU VRAM.
  - Flag any model where the GPU memory limit is not clearly confirmed by the vendor or manufacturer.

How I can help next
- If you’d like, I can monitor and compile a verified AU-focused list with exact SKUs, RAM specs, VRAM allocations, prices, and stock as soon as I have access to up-to-date retailer data.
- Alternatively, I can draft a structured data template you can fill while you or a colleague collect AU retailer pages (Lenovo AU, JB Hi-Fi, Umart, Scorptec, Centre Com, ebay.au) and then I’ll validate and summarize.

Clarifying question
- Do you want me to proceed with gathering live AU retailer data as soon as tools are available, or would you prefer I draft the data template first so you can fill in sources you already have? 

If you want, I can also provide a concise example of how the final table would look once populated.

Citations:
[1]: https://www.reddit.com/r/LocalLLaMA/comments/1fv13rc/amd_strix_halo_rumored_to_have_apu_with_7600_xt/
[2]: https://www.reddit.com/r/AMDLaptops/comments/1hyrivm/where_are_the_strix_halo_laptops/
[3]: https://petronellatech.com/hardware/amd-strix-halo-ai/
[4]: https://toolhalla.ai/blog/amd-strix-halo-local-llm-guide-2026
[5]: https://www.techpowerup.com/324780/amd-strix-halo-processor-boosts-up-to-5-35-ghz-geekbenched
[6]: https://chipsandcheese.com/p/amds-chiplet-apu-an-overview-of-strix
[7]: https://www.ultrabookreview.com/70442-amd-strix-halo-laptops/
[8]: https://news.ycombinator.com/item?id=43361261
[9]: https://news.ycombinator.com/item?id=43360894
[10]: https://www.tomshardware.com/pc-components/cpus/amds-beastly-strix-halo-ryzen-ai-max-debuts-with-radical-new-memory-tech-to-feed-rdna-3-5-graphics-and-zen-5-cpu-cores

---
[Quota] Used 1 Deep Research query (deep_research) | Pro: 0 left | Research: 20 left | EXHAUSTED: Use pplx_smart_query(intent='quick') or pplx_sonar to avoid failures

[Conversation ID: f508f80a-7901-4221-903d-8ece63963a6b]
