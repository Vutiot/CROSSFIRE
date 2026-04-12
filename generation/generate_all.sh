#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# generate_all.sh — Multi-case/multi-source batch orchestration
#
# Iterates over case directories and invokes generate_case.sh for each.
# Can run for a single source or all discovered sources.
#
# Usage:
#   ./generation/generate_all.sh --source ntsb
#   ./generation/generate_all.sh --dry-run
#   ./generation/generate_all.sh
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SOURCE_ID=""
DRY_RUN=false

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [--source SOURCE_ID] [--dry-run]

Orchestrate Claude Code CLI sessions for all cases across one or more sources.

Arguments:
  --source SOURCE_ID   Process only this source (e.g. ntsb, grenfell, copa).
                        If omitted, all sources with agent plans are processed.
  --dry-run            Print what would be done without invoking Claude CLI.

Examples:
  $(basename "$0") --source ntsb
  $(basename "$0") --source grenfell --dry-run
  $(basename "$0")
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
            log_error "Unexpected argument: $1"
            usage 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Discover sources
# ---------------------------------------------------------------------------
declare -a SOURCES=()

if [[ -n "$SOURCE_ID" ]]; then
    PLAN="${PROJECT_ROOT}/generation/sources/${SOURCE_ID}/agent_plan.md"
    if [[ ! -f "$PLAN" ]]; then
        log_error "Agent plan not found for source '${SOURCE_ID}': ${PLAN}"
        exit 1
    fi
    SOURCES=("$SOURCE_ID")
else
    # Discover from generation/sources/*/agent_plan.md
    for plan_file in "${PROJECT_ROOT}"/generation/sources/*/agent_plan.md; do
        if [[ -f "$plan_file" ]]; then
            src_name="$(basename "$(dirname "$plan_file")")"
            SOURCES+=("$src_name")
        fi
    done
    if [[ ${#SOURCES[@]} -eq 0 ]]; then
        log_error "No sources found in generation/sources/*/agent_plan.md"
        exit 1
    fi
fi

log_info "Sources to process: ${SOURCES[*]}"

# ---------------------------------------------------------------------------
# Iterate cases
# ---------------------------------------------------------------------------
TOTAL_START=$(date +%s)
TOTAL_CASES=0
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for src in "${SOURCES[@]}"; do
    CORPUS_DIR="${PROJECT_ROOT}/corpus/${src}"
    if [[ ! -d "$CORPUS_DIR" ]]; then
        log_warn "Corpus directory not found for source '${src}': ${CORPUS_DIR} — skipping"
        continue
    fi

    # Discover case directories (immediate subdirectories of corpus/SOURCE_ID/)
    CASE_FOUND=false
    for case_dir in "${CORPUS_DIR}"/*/; do
        # Skip if the glob didn't match (directory is empty)
        [[ -d "$case_dir" ]] || continue
        CASE_FOUND=true

        case_id="$(basename "$case_dir")"
        TOTAL_CASES=$(( TOTAL_CASES + 1 ))

        # Build arguments
        ARGS=("--source" "$src")
        if [[ "$DRY_RUN" = true ]]; then
            ARGS+=("--dry-run")
        fi
        ARGS+=("$case_dir")

        log_info "Processing ${src}/${case_id} (case ${TOTAL_CASES})..."

        # Invoke generate_case.sh — capture exit code without failing the script
        if "${SCRIPT_DIR}/generate_case.sh" "${ARGS[@]}"; then
            SUCCESS_COUNT=$(( SUCCESS_COUNT + 1 ))
        else
            FAIL_COUNT=$(( FAIL_COUNT + 1 ))
            log_warn "Case ${src}/${case_id} FAILED — continuing to next case"
        fi
    done

    if [[ "$CASE_FOUND" = false ]]; then
        log_warn "No case directories found in ${CORPUS_DIR}"
    fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$(( TOTAL_END - TOTAL_START ))

cat <<EOF

========================================
  Generation Summary
========================================
  Sources:    ${SOURCES[*]}
  Total cases: ${TOTAL_CASES}
  Succeeded:   ${SUCCESS_COUNT}
  Failed:      ${FAIL_COUNT}
  Total time:  ${TOTAL_ELAPSED}s
========================================
EOF

if [[ $FAIL_COUNT -gt 0 ]]; then
    log_warn "${FAIL_COUNT} case(s) failed — review logs above for details"
    exit 1
fi

exit 0
