import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).resolve().parents[1] / "run.sh"
SHA = "a" * 40
snapshot_spec = importlib.util.spec_from_file_location("pipeline_snapshots_integration", SCRIPT.parent / "snapshots.py")
snapshots = importlib.util.module_from_spec(snapshot_spec)
snapshot_spec.loader.exec_module(snapshots)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.work = self.root / "work"
        self.work.mkdir()
        self.issue = self.work / "repo" / "issue-1"
        (self.issue / "logs").mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "calls"
        self.gh = self.bin / "gh"
        self.gh.write_text('''#!/bin/bash
echo "$*" >> "$CALLS"
if [[ "$1" == "api" ]] && [ -n "${SNAPSHOT_FILE:-}" ]; then cat "$SNAPSHOT_FILE"; exit 0; fi
if [[ "$*" == *"issue view"* ]]; then printf '%s\\n' "${LABELS:-}"; exit 0; fi
if [[ "$*" == *"pr view"* ]]; then
  if [[ "$*" == *"baseRefName"* ]]; then printf '%s\\n' "${BASE_NAME:-dev}"
  elif [[ "$*" == *"baseRefOid"* ]]; then
    if [ -n "${BASE_ADVANCE_ON:-}" ]; then
      count=0; [ ! -f "$BASE_COUNTER" ] || count=$(cat "$BASE_COUNTER"); count=$((count+1)); echo "$count" > "$BASE_COUNTER"
      if [ "$count" = "$BASE_ADVANCE_ON" ]; then
        git -C "$ADVANCE_REPO" -c user.name=Test -c user.email=test@example.invalid commit --allow-empty -qm advance >/dev/null 2>&1
        git -C "$ADVANCE_REPO" push -q origin HEAD:dev >/dev/null 2>&1
      fi
    fi
    if [ -n "${REMOTE_GIT:-}" ]; then git --git-dir "$REMOTE_GIT" rev-parse refs/heads/dev; else printf '%s\\n' "${BASE_SHA}"; fi
  elif [ -n "${HEAD_MISMATCH_ONCE:-}" ] && [ ! -e "$HEAD_MISMATCH_ONCE" ]; then touch "$HEAD_MISMATCH_ONCE"; printf '%040d\\n' 2
  elif [ -n "${HEAD_FROM:-}" ]; then git -C "$HEAD_FROM" rev-parse HEAD
  else printf '%s\\n' "${HEAD_SHA}"; fi
  exit 0
fi
exit 0
''')
        self.gh.chmod(0o755)
        pi = self.bin / "pi"
        pi.write_text('''#!/bin/bash
printf '%s\n' "$@" > "$AGENT_ARGS"
if [ "${AGENT_FLOW:-}" = 1 ]; then
  for arg in "$@"; do prompt="$arg"; done
  if [[ "$prompt" == *"身份：Review Agent"* ]]; then
    AGENT_TEXT="PIPELINE_VERDICT: APPROVE"
    if [ -n "${AGENT_ADVANCE_REPO:-}" ] && [ ! -e "$AGENT_ADVANCE_FLAG" ]; then
      git -C "$AGENT_ADVANCE_REPO" -c user.name=Test -c user.email=test@example.invalid commit --allow-empty -qm advance >/dev/null 2>&1
      git -C "$AGENT_ADVANCE_REPO" push -q origin HEAD:dev >/dev/null 2>&1
      touch "$AGENT_ADVANCE_FLAG"
    fi
  else
    if [ "${AGENT_SYNC:-}" = 1 ]; then
      if ! git -c user.name=Test -c user.email=test@example.invalid merge --no-edit origin/dev >/dev/null 2>&1; then
        [ "${AGENT_RESOLVE:-}" = 1 ] || exit 1
        printf 'resolved\\n' > conflict.txt
        git add conflict.txt && git -c user.name=Test -c user.email=test@example.invalid commit -qm 'resolve conflict' || exit 1
      fi
    fi
    if [ "${AGENT_SYNC_REMOTE:-}" = 1 ]; then git -c user.name=Test -c user.email=test@example.invalid merge --no-edit origin/agent/issue-1 >/dev/null 2>&1 || exit 1; fi
    AGENT_TEXT="PIPELINE_RESULT: PR=42"
  fi
fi
if [ -n "${AGENT_MUTATE:-}" ]; then echo changed >> "$AGENT_MUTATE"; fi
if [ -n "${AGENT_TEXT:-}" ]; then jq -nc --arg t "$AGENT_TEXT" '{type:"message_end",message:{role:"assistant",content:[{type:"text",text:$t}]}}'; fi
exit "${AGENT_EXIT:-0}"
''')
        pi.chmod(0o755)
        self.config = self.root / "config.json"
        self.configure()
        self.env = dict(os.environ, PATH=str(self.bin) + ":" + os.environ["PATH"],
                        CALLS=str(self.calls), AGENT_ARGS=str(self.root / "agent-args"), HEAD_SHA=SHA, BASE_SHA=SHA, TMPDIR=str(self.root) + "/")

    def tearDown(self):
        self.tmp.cleanup()

    def configure(self, policy="auto-if-green"):
        self.config.write_text(json.dumps({"work_dir": str(self.work), "agent_cli": "pi",
            "merge_policy": policy, "repos": {"owner/repo": {
                "main_repo_path": str(self.repo), "base_branch": "dev"}}}))

    def run_pipeline(self, *args, **env):
        return subprocess.run([str(SCRIPT), "-c", str(self.config), *args],
                              env=dict(self.env, **env), text=True, capture_output=True)

    def test_noninteractive_missing_answer_is_not_accepted(self):
        (self.issue / "decision-package.json").write_text(json.dumps({"questions": [
            {"id": "Q1", "tier": "ask", "title": "choice", "recommendation": "A", "options": []}]}))
        result = self.run_pipeline("answer", "owner/repo#1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Q1: A", (self.issue / "decision-package.answers.md").read_text())

    def test_stages_use_their_configured_models(self):
        config = json.loads(self.config.read_text())
        config.update(spec_model="local/spec", coding_model="local/coding", review_model="local/review")
        self.config.write_text(json.dumps(config))
        self.prepare_contract()
        args = (self.root / "agent-args").read_text().splitlines()
        self.assertEqual(args[args.index("--model") + 1], "local/spec")
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "fetch", "-q", "origin", "dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "--detach", str(self.issue / "wt"), "origin/dev"], check=True)
        self.run_pipeline("coding", "owner/repo#1", AGENT_TEXT="PIPELINE_RESULT: PR=42", HEAD_FROM=str(self.issue / "wt"))
        args = (self.root / "agent-args").read_text().splitlines()
        self.assertEqual(args[args.index("--model") + 1], "local/coding")
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        review = self.run_pipeline("review", "owner/repo#1", AGENT_TEXT="PIPELINE_VERDICT: APPROVE", REMOTE_GIT=str(remote), HEAD_FROM=str(self.issue / "wt"))
        self.assertEqual(review.returncode, 0, review.stderr)
        args = (self.root / "agent-args").read_text().splitlines()
        self.assertEqual(args[args.index("--model") + 1], "local/review")

    def test_manual_label_blocks_direct_finish(self):
        (self.issue / "state.env").write_text(f"PR=42\nVERDICT=APPROVE\nREVIEW_HEAD={SHA}\nREVIEW_PR=42\nREVIEW_ROUND=1\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        result = self.run_pipeline("finish", "owner/repo#1", LABELS="pipeline/manual")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_finish_rejects_changed_head(self):
        self.prepare_approved_review()
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        result = self.run_pipeline("finish", "owner/repo#1", HEAD_SHA="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_finish_rejects_base_changed_since_review(self):
        self.prepare_approved_review()
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        result = self.run_pipeline("finish", "owner/repo#1", BASE_SHA="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_merge_race_is_reported_as_head_moved(self):
        self.prepare_approved_review()
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        self.gh.write_text('''#!/bin/bash
if [[ "$*" == *"baseRefName"* ]]; then echo dev
elif [[ "$*" == *"baseRefOid"* ]]; then echo "$BASE_SHA"
elif [[ "$*" == *"headRefOid"* ]]; then
  if [ -f "$COUNTFILE" ]; then printf '%040d\\n' 2; else echo "$HEAD_SHA"; fi
elif [[ "$*" == *"pr merge"* ]]; then touch "$COUNTFILE"; exit 1
fi
exit 0
''')
        result = self.run_pipeline("finish", "owner/repo#1", COUNTFILE=str(self.root / "merge-race"))
        self.assertEqual(result.returncode, 8, result.stderr)
        self.assertIn("HEAD_MOVED", result.stderr)

    def test_existing_worktree_must_include_fetched_base(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "fetch", "-q", "origin", "dev"], check=True)
        wt = self.issue / "wt"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "-b", "agent/issue-1", str(wt), "origin/dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "new base"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("coding", "owner/repo#1", AGENT_TEXT="PIPELINE_RESULT: PR=42")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("主分支", result.stderr)

    def test_coding_agent_can_resolve_real_merge_conflict(self):
        (self.repo / "conflict.txt").write_text("original\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "conflict.txt"], check=True)
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "fetch", "-q", "origin", "dev"], check=True)
        wt = self.issue / "wt"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "-b", "agent/issue-1", str(wt), "origin/dev"], check=True)
        (wt / "conflict.txt").write_text("issue change\n")
        subprocess.run(["git", "-C", str(wt), "add", "conflict.txt"], check=True)
        subprocess.run(["git", "-C", str(wt), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "issue"], check=True)
        (self.repo / "conflict.txt").write_text("base change\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "conflict.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("coding", "owner/repo#1", AGENT_FLOW="1", AGENT_SYNC="1", AGENT_RESOLVE="1", HEAD_FROM=str(wt))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((wt / "conflict.txt").read_text(), "resolved\n")
        subprocess.run(["git", "-C", str(wt), "merge-base", "--is-ancestor", "origin/dev", "HEAD"], check=True)

    def test_coding_keeps_uncommitted_work_when_sync_cannot_proceed(self):
        (self.repo / "conflict.txt").write_text("original\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "conflict.txt"], check=True)
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "fetch", "-q", "origin", "dev"], check=True)
        wt = self.issue / "wt"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "-b", "agent/issue-1", str(wt), "origin/dev"], check=True)
        (wt / "conflict.txt").write_text("uncommitted user work\n")
        (self.repo / "conflict.txt").write_text("base change\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "conflict.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("coding", "owner/repo#1", AGENT_FLOW="1", AGENT_SYNC="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((wt / "conflict.txt").read_text(), "uncommitted user work\n")

    def test_coding_rejects_pr_that_does_not_contain_local_result(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "fetch", "-q", "origin", "dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "--detach", str(self.issue / "wt"), "origin/dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("coding", "owner/repo#1", AGENT_TEXT="PIPELINE_RESULT: PR=42")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PR 的 head 不一致", result.stderr)

    def test_coding_preserves_remote_feature_branch_updates(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "fetch", "-q", "origin", "dev"], check=True)
        wt = self.issue / "wt"
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "-b", "agent/issue-1", str(wt), "origin/dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "other contributor"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:refs/heads/agent/issue-1"], check=True)
        self.prepare_contract()
        env = {"AGENT_FLOW": "1", "HEAD_FROM": str(wt)}
        first = self.run_pipeline("coding", "owner/repo#1", **env)
        self.assertNotEqual(first.returncode, 0)
        self.assertIn("远端工作分支", first.stderr)
        second = self.run_pipeline("coding", "owner/repo#1", AGENT_SYNC_REMOTE="1", **env)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        subprocess.run(["git", "-C", str(wt), "merge-base", "--is-ancestor", "origin/agent/issue-1", "HEAD"], check=True)

    def test_review_marks_head_change_for_retry(self):
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        self.gh.write_text('''#!/bin/bash
if [[ "$*" == *"baseRefName"* ]]; then echo dev
elif [[ "$*" == *"baseRefOid"* ]]; then echo "$BASE_SHA"
elif [[ "$*" == *"headRefOid"* ]]; then
  if [ -f "$COUNTFILE" ]; then printf '%040d\\n' 2; else touch "$COUNTFILE"; echo "$HEAD_SHA"; fi
fi
exit 0
''')
        result = self.run_pipeline("review", "owner/repo#1", AGENT_TEXT="PIPELINE_VERDICT: APPROVE", COUNTFILE=str(self.root / "heads"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERDICT=HEAD_MOVED", (self.issue / "state.env").read_text())

    def test_review_marks_head_changed_since_coding_for_retry(self):
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write(f"PR=42\nCODING_HEAD={SHA}\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        result = self.run_pipeline("review", "owner/repo#1", HEAD_SHA="b" * 40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERDICT=HEAD_MOVED", (self.issue / "state.env").read_text())

    def test_loop_resynchronizes_if_base_moves_during_review(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", AGENT_SYNC="1", REMOTE_GIT=str(remote), HEAD_FROM=str(self.issue / "wt"),
                                   AGENT_ADVANCE_REPO=str(self.repo), AGENT_ADVANCE_FLAG=str(self.root / "advanced"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreaterEqual(result.stdout.count("=== ROUND 1: coding ==="), 2)
        self.assertIn("MERGED=42", (self.issue / "state.env").read_text())

    def test_loop_resynchronizes_if_base_moves_after_review(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", AGENT_SYNC="1", REMOTE_GIT=str(remote),
                                   HEAD_FROM=str(self.issue / "wt"), BASE_ADVANCE_ON="3",
                                   BASE_COUNTER=str(self.root / "base-counter"), ADVANCE_REPO=str(self.repo))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreaterEqual(result.stdout.count("=== ROUND 1: coding ==="), 2)
        self.assertIn("MERGED=42", (self.issue / "state.env").read_text())

    def test_loop_retries_when_remote_head_moves_after_coding(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", AGENT_SYNC="1", REMOTE_GIT=str(remote),
                                   HEAD_FROM=str(self.issue / "wt"), HEAD_MISMATCH_ONCE=str(self.root / "mismatch"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreaterEqual(result.stdout.count("=== ROUND 1: coding ==="), 2)

    def test_repeated_base_drift_stops_without_merging(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", AGENT_SYNC="1",
                                   HEAD_FROM=str(self.issue / "wt"), BASE_SHA="b" * 40)
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)
        self.assertIn("达到重试上限", result.stderr)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_interrupted_review_does_not_reuse_previous_approval(self):
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\nVERDICT=APPROVE\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        log = self.issue / "logs/round1-review-output.md"
        log.write_text("PIPELINE_VERDICT: APPROVE\n")
        result = self.run_pipeline("review", "owner/repo#1", AGENT_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual((self.issue / "state.env").read_text().splitlines()[-1], "VERDICT=APPROVE")

    def test_review_with_no_new_result_cannot_reuse_old_events(self):
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\nVERDICT=APPROVE\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        event = {"type": "message_end", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "PIPELINE_VERDICT: APPROVE"}]}}
        (self.issue / "logs/round1-review-output.md.events.jsonl").write_text(json.dumps(event) + "\n")
        result = self.run_pipeline("review", "owner/repo#1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.issue / "state.env").read_text().splitlines()[-1], "VERDICT=MISSING")

    def test_review_then_finish_uses_matching_head(self):
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        review = self.run_pipeline("review", "owner/repo#1", AGENT_TEXT="PIPELINE_VERDICT: APPROVE")
        self.assertEqual(review.returncode, 0, review.stderr)
        finish = self.run_pipeline("finish", "owner/repo#1")
        self.assertEqual(finish.returncode, 0, finish.stderr)
        self.assertIn("--match-head-commit " + SHA, self.calls.read_text())
        self.assertIn("MERGED=42", (self.issue / "state.env").read_text())

    def test_review_stops_when_contract_changes_during_review(self):
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        result = self.run_pipeline("review", "owner/repo#1", AGENT_TEXT="PIPELINE_VERDICT: APPROVE",
                                   AGENT_MUTATE=str(self.issue / "contract.md"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("VERDICT=WAIT", (self.issue / "state.env").read_text())

    def test_interrupted_coding_does_not_reuse_prior_result(self):
        self.prepare_contract()
        (self.issue / "wt").mkdir()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\nVERDICT=APPROVE\n")
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        result = self.run_pipeline("coding", "owner/repo#1", AGENT_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.issue / "state.env").read_text().splitlines()[-1], "VERDICT=MISSING")

    def test_explicit_noninteractive_answer_is_recorded(self):
        (self.issue / "decision-package.json").write_text(json.dumps({"questions": [
            {"id": "Q1", "tier": "ask", "title": "choice", "recommendation": "A", "options": []}]}))
        result = self.run_pipeline("answer", "owner/repo#1", "Q1=B")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Q1: B", (self.issue / "decision-package.answers.md").read_text())

    def test_partial_answers_survive_followup(self):
        (self.issue / "decision-package.json").write_text(json.dumps({"questions": [
            {"id": "Q1", "tier": "ask", "title": "one", "recommendation": "A", "options": []},
            {"id": "Q2", "tier": "ask", "title": "two", "recommendation": "A", "options": []}]}))
        self.assertNotEqual(self.run_pipeline("answer", "owner/repo#1", "Q1=B").returncode, 0)
        result = self.run_pipeline("answer", "owner/repo#1", "Q2=C")
        self.assertEqual(result.returncode, 0, result.stderr)
        answers = (self.issue / "decision-package.answers.md").read_text()
        self.assertIn("Q1: B", answers)
        self.assertIn("Q2: C", answers)

    def test_explicit_auto_override_survives_followup(self):
        (self.issue / "decision-package.json").write_text(json.dumps({"questions": [
            {"id": "Q1", "tier": "auto", "title": "one", "recommendation": "A", "options": []},
            {"id": "Q2", "tier": "ask", "title": "two", "recommendation": "A", "options": []}]}))
        self.assertNotEqual(self.run_pipeline("answer", "owner/repo#1", "Q1=B").returncode, 0)
        result = self.run_pipeline("answer", "owner/repo#1", "Q2=C")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Q1: B", (self.issue / "decision-package.answers.md").read_text())

    def test_spec_rejects_answers_for_changed_decision_package(self):
        pkg = self.issue / "decision-package.json"
        pkg.write_text(json.dumps({"questions": [{"id": "Q1", "tier": "ask", "options": []}]}))
        (self.issue / "decision-package.md").write_text("Q1 context\n")
        self.assertEqual(self.run_pipeline("answer", "owner/repo#1", "Q1=B").returncode, 0)
        pkg.write_text(json.dumps({"questions": [{"id": "Q2", "tier": "ask", "options": []}]}))
        (self.issue / "contract.md").write_text("old contract\n")
        result = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("决策包", result.stderr)
        self.assertEqual(self.run_pipeline("answer", "owner/repo#1", "Q2=C").returncode, 0)
        retry = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertIn("Q2: C", (self.issue / "decision-package.answers.md").read_text())

    def test_spec_rejects_answers_when_markdown_context_changes(self):
        pkg = self.issue / "decision-package.json"
        pkg.write_text(json.dumps({"questions": [{"id": "Q1", "tier": "ask", "options": []}]}))
        md = self.issue / "decision-package.md"
        md.write_text("original context\n")
        self.assertEqual(self.run_pipeline("answer", "owner/repo#1", "Q1=B").returncode, 0)
        md.write_text("materially different context\n")
        (self.issue / "contract.md").write_text("old contract\n")
        result = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertNotEqual(result.returncode, 0)

    def test_legacy_handwritten_answers_remain_available_to_spec(self):
        (self.issue / "decision-package.answers.md").write_text("Q1: B，因为业务要求\n")
        (self.issue / "decision-package.md").write_text("Q1 业务问题\n")
        (self.issue / "contract.md").write_text("contract\n")
        result = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("业务要求", (self.issue / "decision-package.answers.md").read_text())

    def test_spec_rejects_package_change_during_generation(self):
        (self.issue / "decision-package.answers.md").write_text("Q1: B\n")
        pkg = self.issue / "decision-package.md"
        pkg.write_text("original\n")
        (self.issue / "contract.md").write_text("contract\n")
        result = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY", AGENT_MUTATE=str(pkg))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("决策包", result.stderr)

    def test_cleanup_preserves_ignored_files_in_both_worktrees(self):
        (self.repo / ".gitignore").write_text("notes/\n")
        subprocess.run(["git", "-C", str(self.repo), "add", ".gitignore"], check=True)
        self.initialize_repo()
        coding = self.issue / "wt"
        review = self.issue / "review-worktrees" / "round1" / "repo"
        review.parent.mkdir(parents=True)
        for path in (coding, review):
            subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "--detach", str(path)], check=True)
            (path / "notes").mkdir()
            (path / "notes" / "draft.txt").write_text("unsaved")
        (self.issue / "state.env").write_text("PR=42\nMERGED=42\n")
        result = self.run_pipeline("cleanup", "owner/repo#1")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in (coding, review):
            self.assertEqual((path / "notes" / "draft.txt").read_text(), "unsaved")

    def test_decision_change_invalidates_contract_and_review(self):
        self.prepare_approved_review()
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        (self.issue / "decision-package.answers.md").write_text("Q1: B\n")
        first = self.run_pipeline("finish", "owner/repo#1")
        self.assertNotEqual(first.returncode, 0)
        self.assertIn("SPEC_GATE", first.stderr)
        spec = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertEqual(spec.returncode, 0, spec.stderr)
        second = self.run_pipeline("finish", "owner/repo#1")
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("重新审查", second.stderr)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_loop_does_not_use_old_contract_with_unanswered_decision(self):
        (self.issue / "contract.md").write_text("old contract\n")
        (self.issue / "decision-package.answers.md").write_text("Q1: （未答）\n")
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPEC_GATE", result.stderr)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_finish_checks_manual_again_before_merge(self):
        self.prepare_approved_review()
        (self.issue / "logs/round1-coding-output.md").write_text("PIPELINE_RESULT: PR=42\n")
        self.gh.write_text('''#!/bin/bash
echo "$*" >> "$CALLS"
if [[ "$*" == *"issue view"* ]]; then
  if [ -f "$COUNTFILE" ]; then echo pipeline/manual; else touch "$COUNTFILE"; fi
elif [[ "$*" == *"baseRefName"* ]]; then echo dev
elif [[ "$*" == *"pr view"* ]]; then echo "$HEAD_SHA"; fi
''')
        result = self.run_pipeline("finish", "owner/repo#1", COUNTFILE=str(self.root / "count"))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("pr merge", self.calls.read_text())

    def test_cleanup_preserves_independent_and_dirty_worktrees(self):
        self.initialize_repo()
        with tempfile.TemporaryDirectory(prefix="pr-analyze-42-", dir=os.path.realpath("/tmp")) as outside:
            other = Path(outside) / "repo"
            subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "--detach", str(other)], check=True)
            owned = self.issue / "review-worktrees" / "round1" / "repo"
            owned.parent.mkdir(parents=True)
            subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "--detach", str(owned)], check=True)
            (owned / "unsaved.txt").write_text("keep")
            (self.issue / "state.env").write_text("PR=42\nMERGED=42\n")
            result = self.run_pipeline("cleanup", "owner/repo#1")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(other.exists())
            self.assertTrue((owned / "unsaved.txt").exists())
            subprocess.run(["git", "-C", str(self.repo), "worktree", "remove", "--force", str(other)], check=True)

    def test_spec_refuses_unanswered_decision(self):
        (self.issue / "decision-package.answers.md").write_text("Q1: （未答）\n")
        result = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("未回答", result.stderr)

    def initialize_repo(self):
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "init"], check=True)

    def prepare_contract(self):
        (self.issue / "contract.md").write_text("contract\n")
        result = self.run_pipeline("spec", "owner/repo#1", AGENT_TEXT="SPEC_RESULT: READY")
        self.assertEqual(result.returncode, 0, result.stderr)

    def prepare_approved_review(self):
        self.prepare_contract()
        state_file = self.issue / "state.env"
        fingerprint = [line.split("=", 1)[1] for line in state_file.read_text().splitlines()
                       if line.startswith("CONTRACT_READY=")][-1]
        with state_file.open("a") as state:
            state.write(f"PR=42\nVERDICT=APPROVE\nREVIEW_HEAD={SHA}\nREVIEW_BASE={SHA}\nREVIEW_PR=42\nREVIEW_ROUND=1\nREVIEW_CONTRACT={fingerprint}\n")

    def test_loop_runs_from_contract_through_matching_merge(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", REMOTE_GIT=str(remote), HEAD_FROM=str(self.issue / "wt"), LABELS="pipeline/queued")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--remove-label pipeline/queued", self.calls.read_text())
        self.assertIn("--add-label pipeline/in-progress", self.calls.read_text())
        self.assertIn("--match-head-commit ", self.calls.read_text())
        self.assertIn("MERGED=42", (self.issue / "state.env").read_text())

    def test_loop_restores_contract_and_state_from_issue_snapshot(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        self.prepare_contract()
        original = (self.issue / "contract.md").read_bytes()
        payload = snapshots.payload_for(self.issue, "owner/repo", 1, "spec-ready", "dev", self.repo, "a" * 40)
        _, bodies = snapshots.encode_parts(payload)
        api = self.root / "comments.json"
        api.write_text(json.dumps([[{"body": body} for body in bodies]]))
        (self.issue / "contract.md").unlink()
        (self.issue / "state.env").unlink()
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", REMOTE_GIT=str(remote),
                                   HEAD_FROM=str(self.issue / "wt"), SNAPSHOT_FILE=str(api))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("已从 Issue #1 恢复快照", result.stdout)
        self.assertEqual((self.issue / "contract.md").read_bytes(), original)
        self.assertIn("MERGED=42", (self.issue / "state.env").read_text())

    def test_restored_loop_reuses_existing_remote_work_branch(self):
        self.initialize_repo()
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "HEAD:dev"], check=True)
        other = self.root / "other-host"
        subprocess.run(["git", "clone", "-q", "--branch", "dev", str(remote), str(other)], check=True)
        subprocess.run(["git", "-C", str(other), "switch", "-q", "-c", "agent/issue-1"], check=True)
        subprocess.run(["git", "-C", str(other), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "existing work"], check=True)
        subprocess.run(["git", "-C", str(other), "push", "-q", "origin", "HEAD:agent/issue-1"], check=True)
        previous_head = subprocess.check_output(["git", "-C", str(other), "rev-parse", "HEAD"], text=True).strip()
        self.prepare_contract()
        with (self.issue / "state.env").open("a") as state:
            state.write("PR=42\n")
        payload = snapshots.payload_for(self.issue, "owner/repo", 1, "coding-complete", "dev", self.repo, None)
        _, bodies = snapshots.encode_parts(payload)
        api = self.root / "comments.json"
        api.write_text(json.dumps([[{"body": body} for body in bodies]]))
        (self.issue / "contract.md").unlink()
        (self.issue / "state.env").unlink()
        wt = self.issue / "wt"
        result = self.run_pipeline("loop", "owner/repo#1", AGENT_FLOW="1", REMOTE_GIT=str(remote),
                                   HEAD_FROM=str(wt), SNAPSHOT_FILE=str(api))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        subprocess.run(["git", "-C", str(wt), "merge-base", "--is-ancestor", previous_head, "HEAD"], check=True)

    def test_cleanup_unregisters_review_worktree(self):
        self.initialize_repo()
        review = self.issue / "review-worktrees" / "round1" / "repo"
        review.parent.mkdir(parents=True)
        subprocess.run(["git", "-C", str(self.repo), "worktree", "add", "-q", "--detach", str(review)], check=True)
        (self.issue / "state.env").write_text("PR=42\nMERGED=42\n")
        result = self.run_pipeline("cleanup", "owner/repo#1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(review.exists())
        listing = subprocess.check_output(["git", "-C", str(self.repo), "worktree", "list", "--porcelain"], text=True)
        self.assertNotIn(str(review), listing)

if __name__ == "__main__":
    unittest.main()
