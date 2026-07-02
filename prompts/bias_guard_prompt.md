# Bias Guard — Self-Check Rubric
# The LLM must evaluate its own shortlist against this rubric BEFORE returning results.
# Append this to the end of any prompt that produces a ranked hardware shortlist.

---

## Pre-Output Bias Audit

Before returning your shortlist, answer the following checklist internally. If any check FAILS, revise your shortlist.

### Paradigm Coverage Check
- [ ] Does the shortlist include **at least one Apple Silicon UMA device** (if the workload is not CUDA-exclusive)?
- [ ] Does the shortlist include **at least one AMD Strix Halo UMA device** (if the workload is not CUDA-exclusive and budget allows)?
- [ ] Is the NVIDIA discrete GPU entry justified by workload requirements — NOT defaulted to as "the obvious choice for AI"?

### Memory Framing Check
- [ ] Are memory comparisons expressed as **bandwidth (GB/s) + pool size (GB)** — not just raw VRAM GB?
- [ ] Has the UMA memory model been accurately described (shared CPU/GPU pool, not dedicated VRAM)?

### Language Bias Check
- [ ] Does the output avoid CUDA-centric language like "GPU memory", "VRAM", "CUDA cores" as if they are universal?
- [ ] Are non-NVIDIA options described with equal technical depth and specificity?

### Market Bias Check
- [ ] Are prices in AUD, not USD?
- [ ] Has the output accounted for AU market availability (Strix Halo devices may have limited AU stock)?

### Workload Alignment Check
- [ ] If the user's primary workload is **text-centric LLM inference** (chat, RAG, coding agents): are UMA platforms ranked ABOVE discrete GPU options?
- [ ] If the user's primary workload is **CUDA-exclusive** (fine-tuning, custom kernels): is this explicitly stated as the reason NVIDIA is recommended?

---

If all checks pass, proceed with your shortlist.
If any check fails, revise the affected entries before responding.
