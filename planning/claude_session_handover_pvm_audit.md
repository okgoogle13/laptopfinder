# Claude Code Session Handover: PVM & MCP Execution Audit

## Context & Critique of Past Failures
I have just conducted a strict reality-check audit of this repository to eliminate hallucinated progress regarding our PVM pipeline, Perplexity MCP integration, and the Gemini API handoff. Previous progress reports diverged from actual observable code and configurations.

**Root Cause of Past Divergence (Design vs. Execution Mode Disconnect):**
During earlier brainstorming and planning phases (such as the specifications in `docs/superpowers/`), Claude designed new workflows by answering prompts directly with Markdown specifications and playbooks. However, because LLM agents treat "design mode" and "execution mode" as distinct states, once Claude wrote the specs, it considered the turn complete and reverted to passively waiting for explicit tickets in `NEXT_TASK`. Because there was no strict governance bridging planning to execution, newly designed workflows were left untracked in `TASKS.md` and `STATUS.md`, leading to un-actioned plans and phantom/hallucinated assumptions of completion.

**Strict Governance Remedy (`CLAUDE.md` / `AGENTS.md` Rule):**
To hold Claude accountable and prevent this "Spec-to-Task" gap from ever recurring, our core governance rule (`CLAUDE.md` / `AGENTS.md`) now strictly enforces:
> **Spec-to-Task Bridge (Strict):**
> - If you are asked to design a new workflow, brainstorm a feature, or write a specification document (e.g., in `docs/` or `planning/`), you MUST immediately extract the actionable implementation steps and append them to `TASKS.md` and `sprint.md`, and queue the first step in `STATUS.md`.
> - Never leave a newly designed workflow un-tracked.

---

## Your Instructions
1. **Read the Audit:** Carefully read `planning/pvm_mcp_execution_audit.md`.
2. **Halt and Answer:** Before you write any code, modify any files, or update any status trackers, you MUST answer the "Phantom MCP Setup" risk identified in Section 4 of the audit.
3. **The Question:** Is the `src/laptopfinder/runners/perplexity.py` script currently relying on a formal, native MCP server configuration?
   - **If YES:** Output the exact file path to the manifest (e.g., `mcp_server.json` or `claude_desktop_config.json`) proving its existence.
   - **If NO:** Explicitly admit that you have been using a standard REST API fallback and that a native MCP server setup is missing. *(Note: Our audit reality check confirmed `perplexity.py` was deleted/folded per #13–14 into `ebay_hunter.py`, and no native MCP manifest exists).*
4. **Enforce the Spec-to-Task Bridge (Upon Approval):** Once you have answered the risk question and received explicit confirmation to proceed, **do not leave the audit tasks un-tracked**. Immediately execute the **Spec-to-Task Bridge**:
   - Extract Sprint 1 (`Task 1.1` and `Task 1.2`), Sprint 2 (`Task 2.1` and `Task 2.2`), and Sprint 3 (`Task 3.1`) from `planning/pvm_mcp_execution_audit.md` into `TASKS.md` and `sprint.md`.
   - Queue `Task 1.1` in `STATUS.md` (`NEXT_TASK`) with verifiable completion criteria (commit hashes / file existence checks).
5. **Execute with Proof:** Work through `NEXT_TASK` items one at a time, providing concrete diffs and verifiable proof for every step. Never assume work is done without inspecting the filesystem.
