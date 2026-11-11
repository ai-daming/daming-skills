#!/usr/bin/env bash
# issue-pr-pipeline 编排脚本
# 用法: ./run.sh {spec|init|a|b|finish|status} <issue> [round] [options]
# 依赖: bash 4+, jq, gh, 以及 config.json 中配置的 agent CLI（默认 pi）
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SKILL_DIR")"

# ---------- 配置 ----------
CONFIG="${SKILL_DIR}/config.json"
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: 缺少 ${CONFIG}；请复制 config.example.json 为 config.json 并填写" >&2
  exit 1
fi
command -v jq >/dev/null || { echo "ERROR: 需要 jq" >&2; exit 1; }

REPO="$(jq -r .repo "$CONFIG")"
BASE="$(jq -r .base_branch "$CONFIG")"
MAIN_REPO="$(jq -r .main_repo_path "$CONFIG")"
WORK_ROOT="$(jq -r .work_dir "$CONFIG")"
AGENT_CLI="$(jq -r '.agent_cli // "pi"' "$CONFIG")"
MAX_ROUNDS="$(jq -r '.max_rounds // 3' "$CONFIG")"
MERGE_POLICY="$(jq -r '.merge_policy // "manual"' "$CONFIG")"

for req in "$MAIN_REPO" "$WORK_ROOT"; do
  [ -d "$req" ] || { echo "ERROR: 目录不存在: $req（检查 config.json）" >&2; exit 1; }
done
command -v "$AGENT_CLI" >/dev/null 2>&1 || { echo "ERROR: 找不到 agent CLI: ${AGENT_CLI}" >&2; exit 1; }

GRILL_MD="${SKILLS_DIR}/grill/SKILL.md"
PR_ANALYZE_MD="${SKILLS_DIR}/pr-analyze/SKILL.md"
for req in "$GRILL_MD" "$PR_ANALYZE_MD"; do
  [ -f "$req" ] || { echo "ERROR: 缺少兄弟 skill 文件: $req（需与 grill、pr-analyze 同处一个 daming-skills 检出）" >&2; exit 1; }
done

# ---------- 每期状态 ----------
issue="${2:?usage: run.sh <stage> <issue> [round]}"
WORK="${WORK_ROOT}/issue-${issue}"
LOGS="${WORK}/logs"
STATE="${WORK}/state.env"
BRANCH="agent/issue-${issue}"
mkdir -p "${LOGS}"

state_set() { echo "$@" >> "$STATE"; }
state_last() { grep -E "^$1=" "$STATE" 2>/dev/null | tail -1 | cut -d= -f2-; }

LOCK_DIR="${WORK}/.lock"
lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    echo $$ > "${LOCK_DIR}/pid"
    trap 'rm -rf "${LOCK_DIR}"' EXIT
  else
    local pid; pid="$(cat "${LOCK_DIR}/pid" 2>/dev/null || echo '?')"
    if [ "$pid" != "?" ] && ! kill -0 "$pid" 2>/dev/null; then
      echo "WARN: 清理陈旧锁 (pid ${pid})" >&2; rm -rf "${LOCK_DIR}"; mkdir "$LOCK_DIR"; echo $$ > "${LOCK_DIR}/pid"
      trap 'rm -rf "${LOCK_DIR}"' EXIT
    else
      echo "ERROR: issue ${issue} 已有实例在运行 (pid ${pid})；如确认误锁请手动删除 ${LOCK_DIR}" >&2
      exit 9
    fi
  fi
}

render_prompt() { # $1=template $2=dest  占位符来自当前上下文
  sed -e "s#__ISSUE__#${issue}#g" \
      -e "s#__REPO__#${REPO}#g" \
      -e "s#__BASE__#${BASE}#g" \
      -e "s#__BRANCH__#${BRANCH}#g" \
      -e "s#__WORK__#${WORK}#g" \
      -e "s#__SKILLS_DIR__#${SKILLS_DIR}#g" \
      -e "s#__MAIN_REPO__#${MAIN_REPO}#g" \
      -e "s#__GRILL_MD__#${GRILL_MD}#g" \
      -e "s#__PR_ANALYZE_MD__#${PR_ANALYZE_MD}#g" \
      -e "s#__CONTRACT__#${WORK}/contract.md#g" \
      -e "s#__PR__#$(state_last PR)#g" \
      "$1" > "$2"
}

run_agent() { # $1=template $2=session $3=cwd $4=log
  local prompt="${WORK}/$(basename "$4" .md)-prompt.md"
  render_prompt "$1" "$prompt"
  ( cd "$3" && "$AGENT_CLI" --print --session-id "mm${issue}-${2}" "$(cat "$prompt")" ) | tee -a "$4"
}

expect_line() { # $1=file $2=pattern
  grep -E "$2" "$1" | tail -1 || true
}

# ---------- 阶段 ----------
cmd_spec() {
  run_agent "${SKILL_DIR}/prompts/spec-agent.md" spec "$MAIN_REPO" "${LOGS}/spec-output.md" | tail -5
  local verdict; verdict="$(expect_line "${LOGS}/spec-output.md" '^SPEC_RESULT:')"
  echo "SPEC => ${verdict:-缺失输出契约}"
}

cmd_init() {
  git -C "$MAIN_REPO" fetch --no-tags origin "$BASE"
  local wt="${WORK}/wt"
  if [ ! -d "$wt" ]; then
    git -C "$MAIN_REPO" worktree add "$wt" -b "$BRANCH" "origin/${BASE}"
    echo "CREATED worktree=${wt} branch=${BRANCH}"
  else
    echo "EXISTS worktree=${wt}"
  fi
}

cmd_coding() {
  local round="${3:?round required}"
  local template="${SKILL_DIR}/prompts/coding-round1.md"
  if [ "$round" -gt 1 ]; then
    local fb="${LOGS}/round$((round-1))-review-feedback.md"
    [ -f "$fb" ] || { echo "ERROR: 缺上轮反馈 ${fb}" >&2; exit 2; }
    template="${SKILL_DIR}/prompts/coding-fix.md"
    sed "s#__FEEDBACK__#${fb}#" "$template" > "${WORK}/.coding-fix-tpl.md"
    template="${WORK}/.coding-fix-tpl.md"
  fi
  run_agent "$template" coding "${WORK}/wt" "${LOGS}/round${round}-coding-output.md" | tail -5
  local pr; pr="$(expect_line "${LOGS}/round${round}-coding-output.md" 'PIPELINE_RESULT: PR=' | grep -oE '[0-9]+' || true)"
  if [ -n "$pr" ]; then state_set "PR=${pr}"; fi
  echo "CODING round ${round} => $(expect_line "${LOGS}/round${round}-coding-output.md" '^PIPELINE_RESULT:' || echo 缺失输出契约)"
}

cmd_review() {
  local round="${3:?round required}"
  local pr; pr="$(state_last PR)"
  [ -n "$pr" ] || { echo "ERROR: state 无 PR 号，先跑 coding" >&2; exit 2; }
  run_agent "${SKILL_DIR}/prompts/review-agent.md" review "$MAIN_REPO" "${LOGS}/round${round}-review-output.md" | tail -5
  local verdict; verdict="$(expect_line "${LOGS}/round${round}-review-output.md" '^PIPELINE_VERDICT:' | grep -oE '(APPROVE|CHANGES_REQUIRED|WAIT)' || true)"
  state_set "VERDICT=${verdict:-MISSING}"
  case "$verdict" in
    CHANGES_REQUIRED) cp "${LOGS}/round${round}-review-output.md" "${LOGS}/round${round}-review-feedback.md" ;;
  esac
  echo "REVIEW round ${round} => PIPELINE_VERDICT: ${verdict:-缺失输出契约}"
}

cmd_finish() {
  local round="${3:-1}"
  local pr; pr="$(state_last PR)"
  [ -n "$pr" ] || { echo "ERROR: state 无 PR 号" >&2; exit 2; }
  local force="${FORCE:-0}"

  if [ "$MERGE_POLICY" = "auto-if-green" ] && [ "$force" != "1" ]; then
    if ! gh pr checks "$pr" --repo "$REPO" >/dev/null 2>&1; then
      echo "GATES_NOT_GREEN: 按 auto-if-green 策略挂起，需人工拍板（带红合并用 FORCE=1 ./run.sh finish）" >&2
      exit 2
    fi
  fi

  gh pr merge "$pr" --repo "$REPO" --merge
  cat > "${WORK}/.merged-comment.md" <<EOF
PR #${pr} 已通过审查（Review Agent，pr-analyze 协议，第 ${round} 轮）并合并到 ${BASE}。实施契约见本 issue 评论区。需要真机/生产复核的验收点请维护者执行后关闭本单。
EOF
  gh issue comment "$issue" --repo "$REPO" --body-file "${WORK}/.merged-comment.md"
  state_set "MERGED=${pr}"
  echo "MERGED pr=${pr}"
}

cmd_loop() {
  # 全自动循环：在两个人工关口自动停（决策包未决、合并红门）
  if [ ! -f "${WORK}/contract.md" ]; then
    echo "SPEC_GATE: 契约未就绪。先跑 spec 阶段；若已产出 decision-package.md，请收集用户答复写入 decision-package.answers.md 后重跑 spec" >&2
    exit 3
  fi
  cmd_init
  local round=1 pr verdict
  while [ "$round" -le "$MAX_ROUNDS" ]; do
    echo "=== ROUND ${round}: coding ==="
    cmd_coding loop "$issue" "$round"
    pr="$(state_last PR)"
    [ -n "$pr" ] || { echo "NO_PR: coding 未产出 PR，停机等人工" >&2; exit 3; }
    echo "=== ROUND ${round}: review (PR #${pr}) ==="
    cmd_review loop "$issue" "$round"
    verdict="$(state_last VERDICT)"
    case "$verdict" in
      APPROVE)
        if cmd_finish loop "$issue" "$round"; then exit 0; fi
        echo "MERGE_GATE: 门禁未绿或策略为 manual，已挂起；带红合并需用户拍板后 FORCE=1 重跑 finish" >&2
        exit 6 ;;
      CHANGES_REQUIRED)
        gh issue comment "$issue" --repo "$REPO" --body-file "${LOGS}/round${round}-review-feedback.md"
        echo "round ${round} 打回，反馈已评论 issue，进入 round $((round+1))"
        round=$((round+1)) ;;
      *) echo "verdict=${verdict}；停机等人工" >&2; exit 4 ;;
    esac
  done
  echo "MAX_ROUNDS(${MAX_ROUNDS}) 未通过；停机等人工" >&2
  exit 5
}

cmd_status() {
  echo "issue=${issue} repo=${REPO} base=${BASE} branch=${BRANCH}"
  echo "work=${WORK}"
  [ -f "$STATE" ] && cat "$STATE" || echo "(无状态)"
  echo "--- 最近机器行 ---"
  for f in "${LOGS}"/spec-output.md "${LOGS}"/round*-coding-output.md "${LOGS}"/round*-review-output.md; do
    [ -f "$f" ] && echo "$(basename "$f"): $(grep -E '^(SPEC_RESULT|PIPELINE_RESULT|PIPELINE_VERDICT)' "$f" | tail -1)"
  done
}

# ---------- 入口 ----------
stage="${1:?usage: run.sh <spec|init|coding|review|finish|loop|status> <issue> [round]}"
lock
case "$stage" in
  spec)   cmd_spec ;;
  init)   cmd_init ;;
  coding) cmd_coding "$@" ;;
  review) cmd_review "$@" ;;
  finish) cmd_finish "$@" ;;
  loop)   cmd_loop ;;
  status) cmd_status ;;
  *) echo "usage: run.sh <spec|init|coding|review|finish|loop|status> <issue> [round]"; exit 1 ;;
esac
