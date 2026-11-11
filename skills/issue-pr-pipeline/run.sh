#!/usr/bin/env bash
# issue-pr-pipeline 编排脚本
# 用法: ./run.sh [-c <config.json>] <stage> <issue-ref> [round]
#   issue-ref 支持： 123 | owner/repo#123 | owner/repo 123 | https://github.com/owner/repo/issues/123
#   带 repo 时自动解析：优先 config 的 repos 映射（指向本地检出），否则自动 clone 到 work_dir/repos/<name>
# 依赖: bash 4+, jq, gh, 以及 config.json 中配置的 agent CLI（默认 pi）
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SKILL_DIR")"

# ---------- 配置（可用 -c 指定其他项目；默认本目录 config.json） ----------
CONFIG="${SKILL_DIR}/config.json"
if [ "${1:-}" = "-c" ]; then
  CONFIG="${2:?-c 需要路径}"
  shift 2
fi
if [ ! -f "$CONFIG" ]; then
  echo "ERROR: 缺少 ${CONFIG}；请复制 config.example.json 为 config.json 并填写（多项目可建多份，用 -c 选择）" >&2
  exit 1
fi
command -v jq >/dev/null || { echo "ERROR: 需要 jq" >&2; exit 1; }

WORK_ROOT="$(jq -r .work_dir "$CONFIG")"
AGENT_CLI="$(jq -r '.agent_cli // "pi"' "$CONFIG")"
MAX_ROUNDS="$(jq -r '.max_rounds // 3' "$CONFIG")"
MERGE_POLICY="$(jq -r '.merge_policy // "manual"' "$CONFIG")"
CLEANUP_AFTER_MERGE="$(jq -r '.cleanup_after_merge // false' "$CONFIG")"

GRILL_MD="${SKILLS_DIR}/grill/SKILL.md"
PR_ANALYZE_MD="${SKILLS_DIR}/pr-analyze/SKILL.md"
command -v "$AGENT_CLI" >/dev/null 2>&1 || { echo "ERROR: 找不到 agent CLI: ${AGENT_CLI}" >&2; exit 1; }
for req in "$GRILL_MD" "$PR_ANALYZE_MD"; do
  [ -f "$req" ] || { echo "ERROR: 缺少兄弟 skill 文件: $req（需与 grill、pr-analyze 同处一个 daming-skills 检出）" >&2; exit 1; }
done

# ---------- 解析 issue-ref 与仓库 ----------
RAW="${2:?usage: run.sh <stage> <123 | owner/repo#123 | owner/repo 123 | URL> [round]}"
REPO_ARG=""
case "$RAW" in
  http*) REPO_ARG="$(printf '%s' "$RAW" | sed -E 's#https?://[^/]+/([^/]+)/([^/]+)/(issues|pull)/.*#\1/\2#')"; RAW="${RAW##*/}" ;;
  *\#*) REPO_ARG="${RAW%%#*}"; RAW="${RAW##*#}" ;;
  */*)   REPO_ARG="${RAW%%/*}"; RAW="${RAW##*/}" ;;
esac
issue="$RAW"
[[ "$issue" =~ ^[0-9]+$ ]] || { echo "ERROR: 无法从参数解析 issue 号: ${2}" >&2; exit 1; }

if [ -n "$REPO_ARG" ]; then
  REPO="$REPO_ARG"
  MAIN_REPO="$(jq -r --arg r "$REPO" '.repos[$r].main_repo_path // empty' "$CONFIG")"
  BASE="$(jq -r --arg r "$REPO" '.repos[$r].base_branch // empty' "$CONFIG")"
  PROJ_OVERRIDE="$(jq -r --arg r "$REPO" '.repos[$r].project // empty' "$CONFIG")"
  if [ -z "$MAIN_REPO" ]; then
    MAIN_REPO="${WORK_ROOT}/repos/${REPO##*/}"
    if [ ! -d "${MAIN_REPO}/.git" ]; then
      echo "CLONING ${REPO} -> ${MAIN_REPO}（首次自动 clone；已有本地检出可在 config 的 repos 映射指向它）" >&2
      mkdir -p "${MAIN_REPO%/*}"
      gh repo clone "$REPO" "$MAIN_REPO"
    fi
  fi
  if [ -z "$BASE" ]; then
    if git -C "$MAIN_REPO" ls-remote --heads origin dev 2>/dev/null | grep -q .; then BASE=dev
    else BASE="$(gh repo view "$REPO" --json defaultBranchRef --jq .defaultBranchRef.name)"; fi
  fi
else
  REPO="$(jq -r '.repo // empty' "$CONFIG")"
  BASE="$(jq -r '.base_branch // empty' "$CONFIG")"
  MAIN_REPO="$(jq -r '.main_repo_path // empty' "$CONFIG")"
  PROJ_OVERRIDE="$(jq -r '.project // empty' "$CONFIG")"
  [ -n "$REPO" ] && [ -n "$BASE" ] && [ -n "$MAIN_REPO" ] || {
    echo "ERROR: 裸 issue 号需要在 config.json 配 repo/base_branch/main_repo_path，或改用 owner/repo#${issue} 形式" >&2; exit 1; }
fi
[ -d "$WORK_ROOT" ] || { echo "ERROR: 目录不存在: $WORK_ROOT（检查 config 的 work_dir）" >&2; exit 1; }
[ -d "${MAIN_REPO}/.git" ] || { echo "ERROR: 本地主检出不是 git 仓库: $MAIN_REPO" >&2; exit 1; }

# 项目分组目录：避免多项目 issue 号冲突；仅保留 ASCII 安全字符
PROJECT="${PROJ_OVERRIDE:-${REPO##*/}}"
PROJECT="$(printf '%s' "$PROJECT" | sed -e 's/[^A-Za-z0-9._-]/-/g' -e 's/-\{2,\}/-/g' -e 's/^-*//' -e 's/-*$//')"
[ -n "$PROJECT" ] || PROJECT="project"

# ---------- 每期状态 ----------
ISSUE_REF="${REPO}#${issue}"
WORK="${WORK_ROOT}/${PROJECT}/issue-${issue}"
LOGS="${WORK}/logs"
STATE="${WORK}/state.env"
BRANCH="agent/issue-${issue}"
mkdir -p "${LOGS}"

state_set() { echo "$@" >> "$STATE"; }
state_last() { grep -E "^$1=" "$STATE" 2>/dev/null | tail -1 | cut -d= -f2- || true; }

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

stream_filter() { # 从 JSONL 事件流中吐人读进度：工具调用 + 正文流式输出
  while IFS= read -r line; do
    local t; t="$(printf '%s' "$line" | jq -r '.type // empty' 2>/dev/null || true)"
    case "$t" in
      tool_execution_start)
        printf '\n[%s] 🔧 %s\n' "$(date +%H:%M:%S)" "$(printf '%s' "$line" | jq -r '.toolName' 2>/dev/null || true)"
        printf '%s' "$line" | jq -r '(.args // {}) | to_entries[] | "  \(.key): \(.value|tostring)"' 2>/dev/null || true ;;
      message_update)
        local ev; ev="$(printf '%s' "$line" | jq -r '.assistantMessageEvent.type // empty' 2>/dev/null || true)"
        case "$ev" in
          text_start) printf '\n' ;;
          text_delta) printf '%s' "$(printf '%s' "$line" | jq -r '.assistantMessageEvent.delta // empty' 2>/dev/null || true)" ;;
        esac ;;
    esac
  done
}

run_agent() { # $1=template $2=session $3=cwd $4=log
  local prompt="${WORK}/$(basename "$4" .md)-prompt.md"
  render_prompt "$1" "$prompt"
  local evlog="${4}.events.jsonl"
  ( cd "$3" && "$AGENT_CLI" --mode json --session-id "mm${issue}-$2" "$(cat "$prompt")" ) | tee -a "$evlog" | stream_filter || true
  # 从事件流提取全部助手正文（含末尾输出契约行）写入日志
  jq -r 'select(.type == "message_end" and .message.role == "assistant") | .message.content[]? | select(.type == "text") | .text, ""' "$evlog" 2>/dev/null >> "$4" || true
}

expect_line() { # $1=file $2=pattern
  grep -E "$2" "$1" | tail -1 || true
}

# ---------- 阶段 ----------
cmd_spec() {
  run_agent "${SKILL_DIR}/prompts/spec-agent.md" spec "$MAIN_REPO" "${LOGS}/spec-output.md"
  local verdict; verdict="$(expect_line "${LOGS}/spec-output.md" '^SPEC_RESULT:')"
  echo "SPEC => ${verdict:-缺失输出契约}"
  # 人在终端时：出了决策包直接进答题器，答完自动续跑 spec（防止追问死循环，最多链 3 次）
  case "$verdict" in
    *DECISIONS_REQUIRED*)
      if [ -t 0 ] && [ "${SPEC_CHAIN:-0}" -lt 3 ]; then
        export SPEC_CHAIN=$(( ${SPEC_CHAIN:-0} + 1 ))
        cmd_answer "$@"
      else
        echo "下一步： ./run.sh answer ${ISSUE_REF} 逐题拍板（非交互用： ./run.sh answer ${ISSUE_REF} 'Q1=B'）"
      fi ;;
  esac
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
  run_agent "$template" coding "${WORK}/wt" "${LOGS}/round${round}-coding-output.md"
  local pr; pr="$(expect_line "${LOGS}/round${round}-coding-output.md" 'PIPELINE_RESULT: PR=' | grep -oE '[0-9]+' || true)"
  if [ -n "$pr" ]; then state_set "PR=${pr}"; fi
  echo "CODING round ${round} => $(expect_line "${LOGS}/round${round}-coding-output.md" '^PIPELINE_RESULT:' || echo 缺失输出契约)"
}

cmd_review() {
  local round="${3:?round required}"
  local pr; pr="$(state_last PR)"
  [ -n "$pr" ] || { echo "ERROR: state 无 PR 号，先跑 coding" >&2; exit 2; }
  run_agent "${SKILL_DIR}/prompts/review-agent.md" review "$MAIN_REPO" "${LOGS}/round${round}-review-output.md"
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
  if [ "$CLEANUP_AFTER_MERGE" = "true" ]; then
    cmd_cleanup
  fi
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

cmd_cleanup() {
  # 清理该 issue 的重量级产物：Coding worktree + Review 的 /tmp 审查工作树
  # 保留轻量证据：logs/、contract.md、decision-package*、state.env
  local merged; merged="$(state_last MERGED)"
  local force="${FORCE:-0}"
  if [ -z "$merged" ] && [ "$force" != "1" ]; then
    echo "ERROR: state 无 MERGED 记录，拒绝清理（防误删未合并/进行中的工作）；确认放弃用 FORCE=1 ./run.sh cleanup ${issue}" >&2
    exit 2
  fi
  local wt="${WORK}/wt"
  if [ -d "$wt" ]; then
    git -C "$MAIN_REPO" worktree remove "$wt" 2>/dev/null || rm -rf "$wt"
    echo "REMOVED worktree ${wt}"
  fi
  local pr; pr="$(state_last PR)"
  if [ -n "$pr" ]; then
    local tmpdirs
    tmpdirs=$(find /tmp -maxdepth 1 -type d -name "pr-analyze-${pr}-*" 2>/dev/null || true)
    if [ -n "$tmpdirs" ]; then
      echo "$tmpdirs" | while IFS= read -r d; do rm -rf "$d"; echo "REMOVED $d"; done
    fi
  fi
  rm -f "${WORK}/.coding-fix-tpl.md" "${WORK}/.merged-comment.md"
  echo "KEPT 证据文件：logs/ contract.md decision-package*.md state.env（体积小，可长期保留）"
}

cmd_answer() { # 交互答题：逐题选/回车=推荐；或非交互 ./run.sh answer <issue> "Q1=B;Q2=A"
  local answers="${WORK}/decision-package.answers.md"
  local pkg_json="${WORK}/decision-package.json"
  [ -f "$pkg_json" ] || { echo "ERROR: 缺少 ${pkg_json}；先跑 spec 出决策包（旧版决策包无 json，可手写 ${answers}，格式 Q1: B）" >&2; exit 2; }
  : > "$answers"
  local inline="${3:-}"
  if [ -n "$inline" ]; then
    printf '%s\n' "$inline" | tr ';' '\n' | while IFS= read -r pair; do
      local q a; q="${pair%%=*}"; a="${pair#*=}"
      if [ -n "${q// /}" ] && [ -n "$a" ]; then echo "${q}: ${a}" >> "$answers"; fi
    done
  else
    local n; n="$(jq '.questions | length' "$pkg_json")"
    local i=0 id title rec ans
    echo "共 ${n} 题。回车 = 采纳推荐；也可直接输入选项键或写下你的意见。"
    while [ "$i" -lt "$n" ]; do
      id="$(jq -r --argjson i "$i" '.questions[$i].id' "$pkg_json")"
      title="$(jq -r --argjson i "$i" '.questions[$i].title' "$pkg_json")"
      rec="$(jq -r --argjson i "$i" '.questions[$i].recommendation // empty' "$pkg_json")"
      printf '\n%s %s\n' "$id" "$title"
      jq -r --argjson i "$i" '.questions[$i].options[] | "  \(.key)) \(.label)"' "$pkg_json"
      [ -n "$rec" ] && printf '  （推荐 %s）\n' "$rec"
      printf '你的选择: '
      read -r ans
      [ -z "$ans" ] && ans="${rec:-（未答）}"
      echo "${id}: ${ans}" >> "$answers"
      i=$((i+1))
    done
  fi
  echo; echo "答复已保存：${answers}"; sed 's/^/  /' "$answers"
  if [ -t 0 ]; then
    printf '\n现在继续生成实施契约？[Y/n] '
    local go; read -r go
    if [ "${go:-Y}" = "Y" ] || [ "${go:-Y}" = "y" ]; then cmd_spec; fi
  fi
}

cmd_status() {
  echo "issue=${issue} repo=${REPO} base=${BASE} branch=${BRANCH}"
  echo "work=${WORK}"
  [ -f "$STATE" ] && cat "$STATE" || echo "(无状态)"
  echo "--- 最近机器行 ---"
  for f in "${LOGS}"/spec-output.md "${LOGS}"/round*-coding-output.md "${LOGS}"/round*-review-output.md; do
    [ -f "$f" ] && { echo "$(basename "$f"): $(grep -E '^(SPEC_RESULT|PIPELINE_RESULT|PIPELINE_VERDICT)' "$f" | tail -1)" || true; }
  done
}

# ---------- 入口 ----------
stage="${1:?usage: run.sh [-c config.json] <spec|answer|init|coding|review|finish|loop|cleanup|status> <issue> [round|Q1=B...]}"
lock
case "$stage" in
  spec)   cmd_spec ;;
  init)   cmd_init ;;
  coding) cmd_coding "$@" ;;
  review) cmd_review "$@" ;;
  finish) cmd_finish "$@" ;;
  loop)   cmd_loop ;;
  answer) cmd_answer "$@" ;;
  cleanup) cmd_cleanup ;;
  status) cmd_status ;;
  *) echo "usage: run.sh [-c config.json] <spec|init|coding|review|finish|loop|cleanup|status> <issue> [round]"; exit 1 ;;
esac
