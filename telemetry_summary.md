# Gemma 2 Local Memory Telemetry Summary

This document summarizes the quantitative and subjective memory telemetry gathered during real, interactive runs of Gemma 2 models (`gemma2:2b` and `gemma2:9b`) via Ollama on macOS. 

## Test Methodology
- **Interactive Sequence**: 5 distinct prompts were sent to the models sequentially simulating sustained use.
- **Tools**: `ollama run`, background `vm_stat 3`, and before/after `top` PhysMem snapshots.
- **Environment**: Normal stack was open (Antigravity IDE, browser, Claude, Drive).

## Results: Gemma 2 (2B)
**Interactive Prompts Sent**:
1. "Explain Python decorators."
2. "Summarize the history of Unix."
3. "Write a haiku about RAM."
4. "Explain this function and suggest improvements."
5. "Outline a small agentic workflow for Antigravity + Ollama."

**Physical Memory Snapshot (Delta)**:
- **Before**: `PhysMem: 7882M used (2427M wired, 2235M compressor), 307M unused.`
- **After**:  `PhysMem: 7987M used (2425M wired, 2304M compressor), 203M unused.`
- **Delta**: Used memory increased by ~105MB, and the compressor grew by ~69MB. Memory pressure was noticeable but not critical. 

> [!NOTE] 
> **Subjective Assessment (To be filled by human)**
> Add your subjective experience here: Was the IDE sticky? Did browser tabs lag? 
> *e.g., "Mostly usable with minor lag."*

## Results: Gemma 2 (9B)
**Interactive Prompts Sent**: Same 5 prompts to maintain comparable workload.

**Physical Memory Snapshot (Delta)**:
- **Before**: `PhysMem: 8083M used (2427M wired, 2359M compressor), 106M unused.`
- **After**:  `PhysMem: 8153M used (2429M wired, 2545M compressor), 35M unused.`
- **Delta**: The system started the test with only 106M unused RAM. During the test, unused dropped to a critical 35M, and the compressor grew by an additional ~186MB. 

> [!WARNING] 
> **Subjective Assessment (To be filled by human)**
> Add your subjective experience here.
> *e.g., "System became sluggish, swapping heavily, UI responsiveness degraded."*

## Conclusion
The 2B model resulted in a mild increase in memory pressure, largely handled efficiently by the macOS memory compressor. However, the 9B model pushed the 8GB limit significantly, dragging free memory down to 35MB and forcing nearly 2.5GB into the compressor. 

This objective data strongly suggests that running a 9B class model alongside a normal web/IDE stack on an 8GB machine results in critical memory pressure. Moving to a minimum of 16GB (or 32GB/64GB for agentic overhead + IDE) is strongly recommended for seamless local LLM usage.
