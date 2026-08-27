import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from short_factory.artifacts import (
    initialize_machine_revision,
    list_renders,
    load_caption_revision,
    load_current_caption,
    publish_render,
)


def fake_renderer(job_dir, caption, render_dir):
    (render_dir / "short.mp4").write_bytes(b"complete-video")
    (render_dir / "qc.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passed": True,
                "technical_checks_passed": True,
                "content_review": "pending",
                "checks": {"fixture": True},
            }
        ),
        encoding="utf-8",
    )
    return {"engine": "fake"}


class AtomicProcessBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.job_dir = self.root / "jobs" / "fault-job"
        self.job_dir.mkdir(parents=True)
        (self.job_dir / "job.json").write_text(
            json.dumps(
                {
                    "version": 3,
                    "job_id": "fault-job",
                    "duration_seconds": 6.0,
                }
            ),
            encoding="utf-8",
        )
        self.first = initialize_machine_revision(
            self.job_dir,
            [{"start": 0.0, "end": 2.0, "text": "最初の字幕"}],
        )
        self.repo = Path(__file__).resolve().parent.parent

    def tearDown(self):
        self.temporary.cleanup()

    def run_code(self, code, *arguments):
        return subprocess.run(
            [sys.executable, "-c", code, *map(str, arguments)],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_real_process_exit_after_caption_publish_preserves_old_pointer(self):
        cues = [dict(cue) for cue in self.first["cues"]]
        cues[0]["text"] = "強制終了前の完全な新版"
        payload = self.root / "payload.json"
        payload.write_text(json.dumps(cues, ensure_ascii=False), encoding="utf-8")
        pointer = self.job_dir / "subtitles" / "current.json"
        before = pointer.read_bytes()
        code = """
import json, os, sys
from pathlib import Path
from short_factory.artifacts import save_caption_revision
job = Path(sys.argv[1])
cues = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
def failpoint(name):
    if name == 'caption_after_revision_publish':
        os._exit(91)
save_caption_revision(job, base_revision=1, cues=cues, failpoint=failpoint)
"""
        result = self.run_code(code, self.job_dir, payload)
        self.assertEqual(result.returncode, 91, result.stderr.decode(errors="replace"))
        self.assertEqual(before, pointer.read_bytes())
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 1)
        self.assertEqual(load_caption_revision(self.job_dir, 2)["revision"], 2)

    def test_real_process_exit_after_render_qc_never_publishes_partial_render(self):
        old = publish_render(
            self.job_dir,
            caption_revision=1,
            renderer=fake_renderer,
        )
        old_video = self.job_dir / "renders" / old["render_id"] / "short.mp4"
        before = old_video.read_bytes()
        code = """
import json, os, sys
from pathlib import Path
from short_factory.artifacts import publish_render
job = Path(sys.argv[1])
def renderer(job_dir, caption, render_dir):
    (render_dir / 'short.mp4').write_bytes(b'new-complete-video')
    (render_dir / 'qc.json').write_text(json.dumps({'schema_version': 1, 'passed': True, 'technical_checks_passed': True, 'content_review': 'pending', 'checks': {'fixture': True}}), encoding='utf-8')
    return {'engine': 'fake'}
def failpoint(name):
    if name == 'render_after_qc_before_publish':
        os._exit(92)
publish_render(job, caption_revision=1, renderer=renderer, failpoint=failpoint)
"""
        result = self.run_code(code, self.job_dir)
        self.assertEqual(result.returncode, 92, result.stderr.decode(errors="replace"))
        visible = list_renders(self.job_dir)
        self.assertEqual([item["render_id"] for item in visible], [old["render_id"]])
        self.assertEqual(before, old_video.read_bytes())
        self.assertEqual(load_current_caption(self.job_dir)["revision"], 1)


if __name__ == "__main__":
    unittest.main()
