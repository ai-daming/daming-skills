import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "snapshots.py"
spec = importlib.util.spec_from_file_location("pipeline_snapshots", MODULE)
snap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap)


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.dest = self.root / "dest"
        self.comments = []
        self.args = (self.source, "owner/repo", 3, "spec-ready", "main", None, "a" * 40)

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self):
        with patch.object(snap, "get_entries", side_effect=lambda *_: list(self.comments)), patch.object(snap, "post_comment", side_effect=lambda _repo, _issue, body: self.comments.append({"id": len(self.comments) + 1, "body": body})):
            return snap.publish(*self.args)

    def restore(self):
        with patch.object(snap, "get_entries", return_value=list(self.comments)):
            return snap.restore(self.dest, "owner/repo", 3)

    def test_roundtrip_preserves_state_contract_and_resume_feedback(self):
        files = {"state.env": "PR=42\nVERDICT=WAIT\n", "contract.md": "契约\n\n", "decision-package.json": '{"questions":[]}\n',
                 "decision-package.md": "决策\n", "decision-package.answers.md": "Q1: A\n", ".answer-package-hash": "abcdef\n",
                 "logs/round1-coding-output.md": "PIPELINE_RESULT: PR=42\n", "logs/round1-review-feedback.md": "需要修复\n"}
        for name, content in files.items():
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        self.publish()
        meta = self.restore()
        for name, content in files.items():
            self.assertEqual((self.dest / name).read_text(), content)
        self.assertEqual(meta["spec_base_oid"], "a" * 40)

    def test_large_snapshot_splits_and_reassembles(self):
        (self.source / "state.env").write_text("STATE=ready\n")
        (self.source / "contract.md").write_text("A" * 80000)
        self.publish()
        self.assertGreater(len(self.comments), 1)
        self.restore()
        self.assertEqual((self.dest / "contract.md").read_text(), "A" * 80000)

    def test_incomplete_latest_snapshot_does_not_restore_old_state(self):
        (self.source / "state.env").write_text("VERSION=old\n")
        self.publish()
        (self.source / "state.env").write_text("VERSION=new\n")
        (self.source / "contract.md").write_text("B" * 80000)
        payload = snap.payload_for(*self.args)
        _, parts = snap.encode_parts(payload)
        for body in parts[:-1]:
            self.comments.append({"id": len(self.comments) + 1, "body": body})
        with self.assertRaisesRegex(ValueError, "不完整"):
            self.restore()

    def test_unchanged_files_are_referenced_not_repeated(self):
        (self.source / "state.env").write_text("STATE=ready\n")
        (self.source / "contract.md").write_text("契约内容\n")
        self.comments.append({"id": 51, "body": "🤖 流水线自动生成 · 阶段：spec-contract\n\n---\n\n契约内容\n"})
        self.publish()
        (self.source / "state.env").write_text("STATE=coding\n")
        self.publish()
        self.assertEqual(len(self.comments), 3)
        self.assertFalse(any(c["body"].startswith(snap.BUNDLE_HEADER) for c in self.comments))
        latest = snap.decode_group(snap.groups([c["body"] for c in self.comments])[-1])
        self.assertEqual(latest["file_refs"]["contract.md"][0]["comment_id"], "51")
        self.restore()
        self.assertEqual((self.dest / "contract.md").read_text(), "契约内容\n")

    def test_changed_or_deleted_reference_refuses_restore(self):
        (self.source / "state.env").write_text("STATE=ready\n")
        (self.source / "contract.md").write_text("contract\n")
        self.publish()
        self.comments = [c for c in self.comments if not c["body"].startswith(snap.BUNDLE_HEADER)]
        with self.assertRaisesRegex(ValueError, "评论不存在"):
            self.restore()

    def test_restore_does_not_overwrite_existing_work(self):
        (self.source / "state.env").write_text("STATE=ready\n")
        self.publish()
        self.dest.mkdir()
        (self.dest / "state.env").write_text("LOCAL=work\n")
        with self.assertRaisesRegex(ValueError, "本地"):
            self.restore()
        self.assertEqual((self.dest / "state.env").read_text(), "LOCAL=work\n")


if __name__ == "__main__":
    unittest.main()
