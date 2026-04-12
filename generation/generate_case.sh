#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# generate_case.sh — Per-case Claude Code CLI orchestration
#
# Invokes a Claude Code CLI session against a single case directory using
# the source-specific agent plan as the system prompt.
#
# Usage:
#   ./generation/generate_case.sh --source SOURCE_ID CASE_DIR
#   ./generation/generate_case.sh --source ntsb --dry-run corpus/ntsb/WPR19FA080/
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SOURCE_ID=""
CASE_DIR=""
DRY_RUN=false

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") --source SOURCE_ID [--dry-run] CASE_DIR

Orchestrate a Claude Code CLI session for a single case directory.

Arguments:
  --source SOURCE_ID   Source identifier (e.g. ntsb, grenfell, copa). Required.
  --dry-run            Print what would be done without invoking Claude CLI.
  CASE_DIR             Path to the case directory. Required.

Examples:
  $(basename "$0") --source ntsb corpus/ntsb/WPR19FA080/
  $(basename "$0") --source grenfell --dry-run corpus/grenfell/module_1_cladding/
EOF
    exit "${1:-0}"
}

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { echo "[INFO]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warn()  { echo "[WARN]  $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --source)
            SOURCE_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            usage 0
            ;;
        -*)
            log_error "Unknown option: $1"
            usage 1
            ;;
        *)
            if [[ -z "$CASE_DIR" ]]; then
                CASE_DIR="$1"
            else
                log_error "Unexpected argument: $1"
                usage 1
            fi
            shift
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
if [[ -z "$SOURCE_ID" ]]; then
    log_error "Missing required --source SOURCE_ID"
    usage 1
fi

if [[ -z "$CASE_DIR" ]]; then
    log_error "Missing required CASE_DIR argument"
    usage 1
fi

# Resolve CASE_DIR to an absolute path
if [[ ! "$CASE_DIR" = /* ]]; then
    CASE_DIR="${PROJECT_ROOT}/${CASE_DIR}"
fi

if [[ ! -d "$CASE_DIR" ]]; then
    log_error "Case directory does not exist: ${CASE_DIR}"
    exit 1
fi

PLAN_FILE="${PROJECT_ROOT}/generation/sources/${SOURCE_ID}/agent_plan.md"
if [[ ! -f "$PLAN_FILE" ]]; then
    log_error "Agent plan not found: ${PLAN_FILE}"
    exit 1
fi

# ---------------------------------------------------------------------------
# Derive case ID from directory name
# ---------------------------------------------------------------------------
CASE_ID="$(basename "$CASE_DIR")"

# ---------------------------------------------------------------------------
# Ensure chunks exist
# ---------------------------------------------------------------------------
CHUNK_MANIFEST="${CASE_DIR}/chunks/chunk_manifest.json"
if [[ ! -f "$CHUNK_MANIFEST" ]]; then
    log_info "Chunk manifest not found for ${CASE_ID} — running chunking first..."
    if ! python "${PROJECT_ROOT}/generation/chunk_documents.py" --case "${CASE_DIR}"; then
        log_error "Chunking failed for ${CASE_ID}"
        exit 1
    fi
fi

# Count chunks for reporting
CHUNK_COUNT=0
if [[ -f "$CHUNK_MANIFEST" ]]; then
    CHUNK_COUNT=$(python -c "
import json, sys
with open('${CHUNK_MANIFEST}') as f:
    m = json.load(f)
print(m.get('summary', {}).get('total_chunks', 0))
" 2>/dev/null || echo 0)
fi

# ---------------------------------------------------------------------------
# Create output staging directories if needed
# ---------------------------------------------------------------------------
mkdir -p "${CASE_DIR}/anonymized_docs"
mkdir -p "${CASE_DIR}/original_claims"
mkdir -p "${CASE_DIR}/metadata"

# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------
if [[ "$DRY_RUN" = true ]]; then
    cat <<EOF
[DRY-RUN] Would process case: ${CASE_ID}
  Source:      ${SOURCE_ID}
  Case dir:    ${CASE_DIR}
  Plan file:   ${PLAN_FILE}
  Chunks:      ${CHUNK_COUNT}
  Model:       claude-sonnet-4-20250514
  Output dirs: anonymized_docs/, original_claims/, metadata/
EOF
    exit 0
fi

# ---------------------------------------------------------------------------
# Invoke Claude Code CLI
# ---------------------------------------------------------------------------
log_info "Starting generation for ${SOURCE_ID}/${CASE_ID} (${CHUNK_COUNT} chunks)..."
START_TIME=$(date +%s)

if claude -p \
    --system-prompt "$(cat "${PLAN_FILE}")" \
    --model sonnet \
    "Process case directory: ${CASE_DIR}. Read chunks from ${CASE_DIR}/chunks/chunk_manifest.json for fan-out processing. Write all outputs to the case directory."; then
    END_TIME=$(date +%s)
    ELAPSED=$(( END_TIME - START_TIME ))
    log_info "SUCCESS: ${SOURCE_ID}/${CASE_ID} completed in ${ELAPSED}s"
else
    END_TIME=$(date +%s)
    ELAPSED=$(( END_TIME - START_TIME ))
    log_error "FAILED: ${SOURCE_ID}/${CASE_ID} after ${ELAPSED}s"
    exit 1
fi
