#!/usr/bin/env python3
"""Append recoverable Issue history snapshots and restore them on another host."""
import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HEADER = "🤖 流水线自动生成 · 阶段：state-snapshot"
FENCE = "```pipeline-snapshot-json\n"
CHUNK_SIZE = 8000
FILES = ("state.env", "contract.md", "decision-package.md", "decision-package.json",
         "decision-package.answers.md", ".answer-package-hash")


def gh(*args):
    return subprocess.run(["gh", *map(str, args)], check=True, capture_output=True,
                          text=True, timeout=30).stdout


def get_entries(repo, issue):
    data = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/issues/{issue}/comments"))
    return [entry for page in data for entry in page]


def get_comments(repo, issue):
    return [entry.get("body", "") for entry in get_entries(repo, issue)]


def post_comment(repo, issue, body):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as f:
        f.write(body)
        f.flush()
        gh("issue", "comment", issue, "--repo", repo, "--body-file", f.name)


def git_value(path, *args):
    if not path or not Path(path).is_dir():
        return None
    try:
        result = subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                                text=True, timeout=8, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def payload_for(work, repo, issue, stage, base, repo_path, spec_base_oid):
    work = Path(work)
    previous = {}
    previous_file = work / ".restored-snapshot.json"
    if previous_file.is_file():
        previous = json.loads(previous_file.read_text(encoding="utf-8"))
    names = list(FILES)
    logs = work / "logs"
    if logs.is_dir():
        names += [str(p.relative_to(work)) for pattern in ("round*-coding-output.md", "round*-review-feedback.md")
                  for p in sorted(logs.glob(pattern))]
    files = {name: (work / name).read_bytes().decode("utf-8") for name in names if (work / name).is_file()}
    if "state.env" not in files:
        raise ValueError("本地没有 state.env，无法生成快照")
    coding_wt = work / "wt"
    pending_source = previous.get("untransferred_source_status") or previous.get("coding_status") or None
    return {"schema": "issue-pr-pipeline-snapshot-v1", "repo": repo, "issue": int(issue),
            "stage": stage, "base_branch": base, "spec_base_oid": spec_base_oid or previous.get("spec_base_oid") or None,
            "source_checkout_head": git_value(repo_path, "rev-parse", "HEAD"),
            "known_tracking_base": git_value(repo_path, "rev-parse", "--verify", f"refs/remotes/origin/{base}"),
            "coding_head": git_value(coding_wt, "rev-parse", "HEAD"),
            "coding_status": git_value(coding_wt, "status", "--porcelain"),
            "untransferred_source_status": pending_source,
            "files": files}


def encode_parts(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ident = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    chunks = [raw[i:i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)] or [""]
    result = []
    for i, chunk in enumerate(chunks, 1):
        part = json.dumps({"id": ident, "part": i, "total": len(chunks), "data": chunk}, ensure_ascii=False, separators=(",", ":"))
        summary = f"{HEADER}\n\n快照：{payload['stage']}；目标：{payload['repo']}#{payload['issue']}；分片：{i}/{len(chunks)}\n"
        if i == 1:
            if payload.get("historical_created_at"):
                summary += f"原快照时间：{payload['historical_created_at']}（本评论为迁移记录）\n"
            state = payload["files"]["state.env"]
            if len(state) <= 4000:
                summary += f"\n记录的原始状态：\n```text\n{state}\n```\n"
            else:
                summary += "\n状态较长，完整原文保存在下方快照分片。\n"
            summary += f"\n历史 Spec 基线：{payload['spec_base_oid'] or '未记录'}；拍摄时本地检出：{payload['source_checkout_head'] or '未记录'}。\n"
        result.append(summary + "\n" + FENCE + part + "\n```")
    return ident, result


def decode_part(body):
    if not body.startswith(HEADER) or FENCE not in body or not body.endswith("\n```"):
        return None
    try:
        item = json.loads(body.rsplit(FENCE, 1)[1][:-4])
        if not re.fullmatch(r"[0-9a-f]{64}", item["id"]) or not (1 <= item["part"] <= item["total"]):
            return None
        if not isinstance(item["data"], str):
            return None
        return item
    except (ValueError, TypeError, KeyError):
        return None


def groups(comments):
    result = []
    by_id = {}
    for body in comments:
        part = decode_part(body)
        if not part:
            if body.startswith(HEADER):
                raise ValueError("快照格式损坏")
            continue
        ident = part["id"]
        if ident not in by_id:
            by_id[ident] = {"id": ident, "total": part["total"], "parts": {}}
            result.append(by_id[ident])
        group = by_id[ident]
        if group["total"] != part["total"] or (part["part"] in group["parts"] and group["parts"][part["part"]] != part["data"]):
            raise ValueError("快照分片冲突")
        group["parts"][part["part"]] = part["data"]
    return result


def decode_group(group):
    if len(group["parts"]) != group["total"]:
        raise ValueError("最新快照不完整，不能恢复旧状态")
    raw = "".join(group["parts"][n] for n in range(1, group["total"] + 1))
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != group["id"]:
        raise ValueError("快照内容不完整")
    return json.loads(raw)


BUNDLE_HEADER = "🤖 流水线自动生成 · 阶段：snapshot-files"
BUNDLE_FENCE = "```pipeline-files-json\n"
TRACE_SEPARATOR = "\n\n---\n\n"


def digest(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def contents_in_entry(entry):
    body = entry.get("body") or ""
    if body.startswith(BUNDLE_HEADER) and BUNDLE_FENCE in body and body.endswith("\n```"):
        try:
            item = json.loads(body.rsplit(BUNDLE_FENCE, 1)[1][:-4])
            raw = gzip.decompress(base64.b64decode(item["gzip_base64"], validate=True))
            files = json.loads(raw)
            if isinstance(files, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
                return list(files.values())
        except (ValueError, KeyError, TypeError, OSError):
            raise ValueError("快照文件包损坏")
    if body.startswith("🤖 流水线自动生成 · 阶段：spec-") and TRACE_SEPARATOR in body:
        return [body.split(TRACE_SEPARATOR, 1)[1]]
    return []


def file_index(entries):
    result = {}
    for entry in entries:
        if not entry.get("id"):
            continue
        for content in contents_in_entry(entry):
            result.setdefault(digest(content), str(entry["id"]))
    return result


def bundle_body(files):
    raw = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii")
    return BUNDLE_HEADER + "\n\n恢复所需的文件内容包；相同内容只保存一次。\n\n" + BUNDLE_FENCE + json.dumps({"gzip_base64": encoded}, separators=(",", ":")) + "\n```"


def compact_payload(payload, repo, issue):
    entries = get_entries(repo, issue)
    index = file_index(entries)
    files = payload["files"]
    chunks = {}
    missing = {}
    for name, content in files.items():
        if name == "state.env":
            continue
        if digest(content) in index or len(bundle_body({name: content})) <= 60000:
            chunks[name] = [content]
        else:
            chunks[name] = [content[i:i + 12000] for i in range(0, len(content), 12000)]
        for part in chunks[name]:
            h = digest(part)
            if h not in index:
                missing[h] = part
    # Batch previously unseen file content into as few comments as possible.
    batch = {}
    for h, content in missing.items():
        candidate = {**batch, h: content}
        if batch and len(bundle_body(candidate)) > 60000:
            post_comment(repo, issue, bundle_body(batch))
            batch = {h: content}
        else:
            batch = candidate
    if batch:
        post_comment(repo, issue, bundle_body(batch))
    if missing:
        entries = get_entries(repo, issue)
        index = file_index(entries)
    refs = {}
    for name, parts in chunks.items():
        refs[name] = []
        for part in parts:
            h = digest(part)
            if h not in index:
                raise ValueError(f"文件回读失败：{name}")
            refs[name].append({"comment_id": index[h], "sha256": h})
    return {**payload, "schema": "issue-pr-pipeline-snapshot-v2", "files": {"state.env": files["state.env"]}, "file_refs": refs}


def expand_payload(payload, entries):
    if payload.get("schema") == "issue-pr-pipeline-snapshot-v1":
        return payload
    if payload.get("schema") != "issue-pr-pipeline-snapshot-v2":
        raise ValueError("不支持的快照版本")
    by_id = {str(e.get("id")): e for e in entries}
    files = dict(payload.get("files", {}))
    for name, refs in payload.get("file_refs", {}).items():
        parts = []
        for ref in refs:
            entry = by_id.get(str(ref.get("comment_id")))
            if not entry:
                raise ValueError(f"快照引用的评论不存在：{name}")
            matches = [v for v in contents_in_entry(entry) if digest(v) == ref.get("sha256")]
            if not matches:
                raise ValueError(f"快照引用的文件已变化：{name}")
            parts.append(matches[0])
        files[name] = "".join(parts)
    return {**payload, "files": files}


def publish_payload(payload, repo, issue):
    compact = compact_payload(payload, repo, issue)
    ident, bodies = encode_parts(compact)
    existing = next((g for g in groups(get_comments(repo, issue)) if g["id"] == ident), None)
    done = existing["parts"] if existing else {}
    for index, body in enumerate(bodies, 1):
        if index not in done:
            post_comment(repo, issue, body)
    entries = get_entries(repo, issue)
    latest = next((g for g in groups([e.get("body", "") for e in entries]) if g["id"] == ident), None)
    if not latest or expand_payload(decode_group(latest), entries)["files"] != payload["files"]:
        raise ValueError("快照回读失败")
    print(f"Issue #{issue} 快照已回写并核对：{payload['stage']} ({len(bodies)} 条评论)")
    return ident


def publish(work, repo, issue, stage, base, repo_path, spec_base_oid=None):
    return publish_payload(payload_for(work, repo, issue, stage, base, repo_path, spec_base_oid), repo, issue)


def restore(work, repo, issue):
    entries = get_entries(repo, issue)
    found = groups([e.get("body", "") for e in entries])
    if not found:
        raise ValueError("Issue 上没有可恢复的流水线快照")
    payload = expand_payload(decode_group(found[-1]), entries)
    if payload.get("repo") != repo or payload.get("issue") != int(issue):
        raise ValueError("快照目标不匹配")
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise ValueError("快照文件格式无效")
    allowed = set(FILES)
    for name, content in files.items():
        if name not in allowed and not re.fullmatch(r"logs/round[0-9]+-(?:coding-output|review-feedback)\.md", name):
            raise ValueError("快照包含无法恢复的文件")
        if not isinstance(content, str):
            raise ValueError("快照文件格式无效")
        target = Path(work) / name
        if target.exists() and target.read_bytes() != content.encode("utf-8"):
            raise ValueError(f"本地已有不同内容，未覆盖：{name}")
    if "state.env" not in files:
        raise ValueError("快照没有状态文件")
    for name, content in files.items():
        target = Path(work) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(content.encode("utf-8"))
    meta = {k: v for k, v in payload.items() if k != "files"}
    (Path(work) / ".restored-snapshot.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已从 Issue #{issue} 恢复快照：{payload['stage']}；历史 Spec 基线：{payload.get('spec_base_oid') or '未记录'}")
    if payload.get("coding_status") or payload.get("untransferred_source_status"):
        print("WARN: 原工作区曾有未提交或未跟踪内容；快照未携带文件本体，请结合原工作区或 PR 核对。", file=sys.stderr)
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("publish", "restore"))
    parser.add_argument("--work", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--stage", default="manual")
    parser.add_argument("--base", default="main")
    parser.add_argument("--repo-path")
    parser.add_argument("--spec-base")
    a = parser.parse_args()
    try:
        if a.action == "publish":
            publish(a.work, a.repo, a.issue, a.stage, a.base, a.repo_path, a.spec_base)
        else:
            restore(a.work, a.repo, a.issue)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"快照操作失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
