#!/usr/bin/env bash
set -euo pipefail

# =========================
# Config
# =========================
CLAUDE_CMD="${CLAUDE_CMD:-claude}"     # e.g. claude
OUT_DIR="${OUT_DIR:-.ai/out}"          # outputs
AGENT_ROOT="${AGENT_ROOT:-.ai/agents}" # agents
TEMPLATE_ROOT="${TEMPLATE_ROOT:-.ai/templates}"

mkdir -p "$OUT_DIR"

# =========================
# Helpers
# =========================
die() { echo "❌ $*" >&2; exit 1; }

need_file() {
  [[ -f "$1" ]] || die "Missing file: $1"
}

# Detect CLI flags for prompt/system
detect_flags() {
  # Default assumption
  PROMPT_FLAG="--prompt"
  SYSTEM_FLAG="--system"

  if ! command -v "$CLAUDE_CMD" >/dev/null 2>&1; then
    die "Claude CLI not found: $CLAUDE_CMD (set CLAUDE_CMD env or install it)"
  fi

  local help_txt
  help_txt="$("$CLAUDE_CMD" --help 2>/dev/null || true)"

  # Some CLIs use -p/-S, some use --prompt/--system.
  # We'll detect what exists in help text.
  if echo "$help_txt" | grep -qE '(^|[[:space:]])-p([[:space:]]|,|$)'; then
    PROMPT_FLAG="-p"
  fi
  if echo "$help_txt" | grep -qE '(^|[[:space:]])-S([[:space:]]|,|$)'; then
    SYSTEM_FLAG="-S"
  fi

  # If it doesn't mention --system, fall back to no system (rare)
  if ! echo "$help_txt" | grep -q -- "--system" && [[ "$SYSTEM_FLAG" == "--system" ]]; then
    # keep default; some CLIs don't show it in help. We'll handle failure later.
    true
  fi
}

run_agent() {
  local agent_name="$1"  # e.g. general-purpose
  local prompt_text="$2"
  local out_file="$3"

  local agent_file="$AGENT_ROOT/$agent_name.md"
  need_file "$agent_file"

  mkdir -p "$(dirname "$out_file")"

  echo "==> [$agent_name] -> $out_file"

  # Try with system+prompt first
  set +e
  "$CLAUDE_CMD" \
    "$SYSTEM_FLAG" "$(cat "$agent_file")" \
    "$PROMPT_FLAG" "$prompt_text" \
    > "$out_file" 2> "$OUT_DIR/$agent_name.stderr"
  local rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    echo "⚠️  [$agent_name] first attempt failed (rc=$rc). Retrying without system prompt..." >&2
    set +e
    "$CLAUDE_CMD" \
      "$PROMPT_FLAG" "$(printf "%s\n\n[System instructions]\n%s\n" "$prompt_text" "$(cat "$agent_file")")" \
      > "$out_file" 2>> "$OUT_DIR/$agent_name.stderr"
    rc=$?
    set -e
  fi

  if [[ $rc -ne 0 ]]; then
    echo "----- STDERR ($agent_name) -----" >&2
    tail -n 200 "$OUT_DIR/$agent_name.stderr" >&2 || true
    die "Agent failed: $agent_name"
  fi
}

git_diff_or_empty() {
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git diff || true
  else
    echo ""
  fi
}

# =========================
# Main: parse input
# =========================
REQ=""
if [[ "${1:-}" == "-f" ]]; then
  [[ -n "${2:-}" ]] || die "Usage: $0 -f request.md"
  need_file "$2"
  REQ="$(cat "$2")"
else
  REQ="${1:-}"
fi

[[ -n "$REQ" ]] || die "Usage: $0 \"your requirement\"  OR  $0 -f request.md"

detect_flags

# =========================
# Pipeline steps
# =========================
# 1) analysis
run_agent "general-purpose" "$REQ" "$OUT_DIR/analysis.md"

# 2) design
DESIGN_PROMPT="$(cat "$OUT_DIR/analysis.md")"
run_agent "design-agent" "$DESIGN_PROMPT" "$OUT_DIR/design-spec.md"

# 3) implement
IMPLEMENT_PROMPT="$(cat "$OUT_DIR/design-spec.md")

仓库上下文（执行说明）：
- 你正在一个代码仓库中工作（当前目录）。
- 实现时遵循“最小改动原则”，优先复用已有代码。
- 输出：变更摘要、变更文件清单、如何运行/如何测试的命令。
"
run_agent "task-executor" "$IMPLEMENT_PROMPT" "$OUT_DIR/implementation-report.md"

# 4) review (spec + implementation + diff)
DIFF_TXT="$(git_diff_or_empty)"
REVIEW_PROMPT="$(cat "$OUT_DIR/design-spec.md")

--- IMPLEMENTATION REPORT ---
$(cat "$OUT_DIR/implementation-report.md")

--- GIT DIFF ---
$DIFF_TXT
"
run_agent "code-reviewer" "$REVIEW_PROMPT" "$OUT_DIR/code-review.md"

echo
echo "✅ Pipeline finished. Outputs:"
echo "  - $OUT_DIR/analysis.md"
echo "  - $OUT_DIR/design-spec.md"
echo "  - $OUT_DIR/implementation-report.md"
echo "  - $OUT_DIR/code-review.md"
echo
echo "Tip: Check stderr logs in $OUT_DIR/*.stderr if anything looks off."
