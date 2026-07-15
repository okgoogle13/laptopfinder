#!/usr/bin/env bash

# Usage:
#   ./run_gemma_test.sh 2b
#   ./run_gemma_test.sh 9b
#
# This script:
#   - Logs vm_stat every 3 seconds to a file
#   - Captures before/during PhysMem snapshots
#   - Runs an interactive Gemma 2 session (2B or 9B)
#   - Stops logging when you exit the model

set -e

MODEL_SIZE="$1"

if [ -z "$MODEL_SIZE" ]; then
  echo "Usage: $0 2b|9b"
  exit 1
fi

MODEL_NAME="gemma2:${MODEL_SIZE}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
VM_LOG="vmstat-log-${MODEL_SIZE}-${TIMESTAMP}.txt"
PHYS_LOG="physmem-log-${MODEL_SIZE}-${TIMESTAMP}.txt"

echo "=== Gemma 2 ${MODEL_SIZE} test starting at ${TIMESTAMP} ==="
echo "Model: ${MODEL_NAME}"
echo "vm_stat log:    ${VM_LOG}"
echo "PhysMem log:    ${PHYS_LOG}"
echo

# 1) Make sure the model is pulled
echo "[*] Checking/pulling model ${MODEL_NAME}..."
if ollama pull "${MODEL_NAME}"; then
  echo "[*] Model ${MODEL_NAME} present and ready."
else
  echo "[!] Failed to pull ${MODEL_NAME}, aborting run."
  exit 1
fi

# 2) Start vm_stat logging in the background
echo "[*] Starting vm_stat logging to ${VM_LOG} (Ctrl+C will stop it later)..."
vm_stat 3 > "${VM_LOG}" &
VM_PID=$!
echo "[*] vm_stat PID: ${VM_PID}"
echo

# 3) Capture initial PhysMem snapshot
echo "[*] Capturing initial PhysMem snapshot..."
top -l 1 -s 0 | grep PhysMem >> "${PHYS_LOG}"
echo "[*] Initial PhysMem written to ${PHYS_LOG}"
echo

# 4) Run interactive Ollama session
echo "======================================================="
echo "[*] Starting interactive session: ollama run ${MODEL_NAME}"
echo "[*] Keep Antigravity/IDE, browser, Claude, Drive open."
echo "[*] Ask several real prompts (explain code, summarise text, etc.)."
echo "[*] When you're done, press Ctrl+C to exit the model."
echo "======================================================="
echo

# Disable exit on error temporarily so we can gracefully cleanup if ollama run fails or is interrupted
set +e
ollama run "${MODEL_NAME}"
set -e

# 5) After interactive session ends, capture final PhysMem snapshot
echo
echo "[*] Interactive session ended. Capturing final PhysMem snapshot..."
top -l 1 -s 0 | grep PhysMem >> "${PHYS_LOG}"
echo "[*] Final PhysMem written to ${PHYS_LOG}"

# 6) Stop vm_stat logging
echo "[*] Stopping vm_stat (PID ${VM_PID})..."
kill "${VM_PID}" 2>/dev/null || echo "[*] vm_stat already stopped."

echo
echo "=== Gemma 2 ${MODEL_SIZE} test complete ==="
echo "vm_stat log:    ${VM_LOG}"
echo "PhysMem log:    ${PHYS_LOG}"
echo "Review these logs plus how the machine felt (lag, swap, etc.)."
