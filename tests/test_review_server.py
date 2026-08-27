import hashlib
import http.client
import io
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from short_factory import review_server
from short_factory.artifacts import caption_hash, initialize_machine_revision
from short_factory.candidate_artifacts import (
    publish_candidate_set,
    update_status as update_candidate_status,
)
from short_factory.composition_artifacts import (
    create_composition_project,
    load_current_edit,
    publish_edit_revision,
)


def create_directory_link(link: Path, target: Path) -> None:
    failure: OSError | None = None
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except OSError as exc:
        failure = exc
        if os.name != "nt":
            raise
    result = subprocess.run(
        ["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        assert failure is not None
        raise failure


class FakeLauncher:
    def __init__(self):
        self.calls = []
        self.operations = {
            "saveoperation0001": {
                "status": "complete",
                "result": {"revision": 2},
            },
            "renderoperation01": {
                "status": "complete",
                "result": {"render_id": "render2"},
            },
            "adoptoperation001": {
                "status": "complete",
                "result": {
                    "job_id": "clip-001-fixture",
                    "project_id": "clip-001-fixture",
                    "render_id": "render3",
                },
            },
            "compositionsave01": {
                "status": "complete",
                "result": {"project_id": "composition1", "revision": 2},
            },
            "compositionrender01": {
                "status": "complete",
                "result": {"render_id": "composition-render2"},
            },
        }

    def launch_save(self, job_id, payload):
        self.calls.append(("save", job_id, payload))
        return review_server.LaunchOutcome("LOCK_ACQUIRED", "saveoperation0001")

    def launch_render(self, job_id, revision):
        self.calls.append(("render", job_id, revision))
        return review_server.LaunchOutcome("LOCK_ACQUIRED", "renderoperation01")

    def launch_candidate_adopt(self, run_id, candidate_id, start, end):
        self.calls.append(("adopt", run_id, candidate_id, start, end))
        return review_server.LaunchOutcome("LOCK_ACQUIRED", "adoptoperation001")

    def get_status(self, operation_id):
        return self.operations.get(operation_id)

    def launch_composition_save(self, projects_root, project_id, payload):
        self.calls.append(("composition-save", projects_root, project_id, payload))
        return review_server.LaunchOutcome("LOCK_ACQUIRED", "compositionsave01")

    def launch_composition_render(
        self, projects_root, project_id, edit_revision, render_profile
    ):
        self.calls.append(
            (
                "composition-render",
                projects_root,
                project_id,
                edit_revision,
                render_profile,
            )
        )
        return review_server.LaunchOutcome("LOCK_ACQUIRED", "compositionrender01")


class FakeCandidateLauncher:
    def __init__(self, succeeds=True):
        self.calls = []
        self.succeeds = succeeds

    def launch(self, run_id):
        self.calls.append(run_id)
        return self.succeeds


class ReviewServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.jobs_root = Path(self.temporary.name) / "jobs"
        self.job_dir = self.jobs_root / "job1"
        self.job_dir.mkdir(parents=True)
        (self.job_dir / "job.json").write_text(
            json.dumps(
                {
                    "version": 3,
                    "job_id": "job1",
                    "duration_seconds": 2.4,
                    "config": {"subtitle": {"min_cue_seconds": 0.7}},
                }
            ),
            encoding="utf-8",
        )
        self.caption = initialize_machine_revision(
            self.job_dir,
            [
                {"start": 0.0, "end": 1.2, "text": "元の字幕"},
                {"start": 1.2, "end": 2.4, "text": "二行目"},
            ],
        )
        self.video_path = self.job_dir / "renders" / "render1" / "short.mp4"
        self.video_path.parent.mkdir(parents=True)
        self.video_bytes = b"0123456789abcdefghijklmnopqrstuvwxyz"
        self.video_path.write_bytes(self.video_bytes)
        self.output_hash = hashlib.sha256(self.video_bytes).hexdigest()
        self.render = {
            "schema_version": 1,
            "render_id": "render1",
            "job_id": "job1",
            "caption_revision": 1,
            "caption_hash": caption_hash(self.caption),
            "output_hash": self.output_hash,
            "technical_checks_passed": True,
            "content_review": "pending",
            "created_at": "2026-08-12T00:00:00+00:00",
        }
        (self.video_path.parent / "render.json").write_text(
            json.dumps(self.render), encoding="utf-8"
        )
        (self.video_path.parent / "qc.json").write_text(
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
        self.launcher = FakeLauncher()
        self.candidate_launcher = FakeCandidateLauncher()
        self.composition_root = Path(self.temporary.name) / "composition-projects"
        self.composition_source = Path(self.temporary.name) / "composition-source.mp4"
        self.composition_source.write_bytes(b"composition-source-fixture")
        ffmpeg = Path(self.temporary.name) / "ffmpeg.exe"
        ffprobe = Path(self.temporary.name) / "ffprobe.exe"
        ffmpeg.write_bytes(b"tool")
        ffprobe.write_bytes(b"tool")
        config = json.loads(
            (Path(__file__).resolve().parents[1] / "config" / "templates" / "default.json").read_text(
                encoding="utf-8"
            )
        )
        create_composition_project(
            self.composition_root,
            "composition1",
            source_path=self.composition_source,
            rights_confirmed=True,
            authorization_note="test fixture",
            config=config,
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
            probe=lambda _source, _ffprobe: {
                "format": {"start_time_num": 0, "start_time_den": 1},
                "video": {
                    "stream_index": 0,
                    "time_base_num": 1,
                    "time_base_den": 30,
                    "start_pts": 0,
                    "duration_ts": 900,
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30/1",
                    "real_frame_rate": "30/1",
                    "variable_frame_rate": False,
                },
                "audio": {
                    "stream_index": 1,
                    "time_base_num": 1,
                    "time_base_den": 48000,
                    "start_pts": 0,
                    "sample_rate": 48000,
                    "channels": 2,
                    "duration_samples": 1440000,
                },
            },
        )
        plan = json.loads(
            (Path(__file__).resolve().parent / "fixtures" / "composition" / "dialogue.json").read_text(
                encoding="utf-8"
            )
        )
        plan["project_id"] = "composition1"
        publish_edit_revision(
            self.composition_root / "composition1",
            plan,
            base_revision=None,
        )

        self.server = review_server.create_review_server(
            self.jobs_root,
            port=0,
            composition_projects_root=self.composition_root,
            launch_token="launch-token-for-test",
            launcher=self.launcher,
            candidate_launcher=self.candidate_launcher,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = self.server.expected_host
        self.origin = self.server.origin
        self.cookie = ""
        self.csrf = ""

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method, path, *, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_address[1], timeout=3
        )
        request_headers = {"Host": self.host}
        if headers:
            request_headers.update(headers)
        encoded = None
        if body is not None:
            if isinstance(body, bytes):
                encoded = body
            else:
                encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json")
            request_headers["Content-Length"] = str(len(encoded))
        connection.request(method, path, body=encoded, headers=request_headers)
        response = connection.getresponse()
        data = response.read()
        headers_out = dict(response.getheaders())
        status = response.status
        connection.close()
        return status, headers_out, data

    def authenticate(self):
        status, headers, data = self.request(
            "POST",
            "/api/session",
            body={"launch_token": "launch-token-for-test"},
            headers={"Origin": self.origin},
        )
        self.assertEqual(status, 200, data)
        self.cookie = headers["Set-Cookie"].split(";", 1)[0]
        self.csrf = json.loads(data)["csrf_token"]

    def auth_headers(self, *, mutation=False):
        headers = {"Cookie": self.cookie}
        if mutation:
            headers.update({"Origin": self.origin, "X-CSRF-Token": self.csrf})
        return headers

    def create_candidate_run(self, source_bytes):
        status, _, data = self.request(
            "POST",
            "/api/candidate-runs",
            body={
                "file": {
                    "name": "../../display-only.mp4",
                    "size_bytes": len(source_bytes),
                    "content_type": "video/mp4",
                    "last_modified_ms": 1,
                },
                "rights": {
                    "edit_analysis_confirmed": True,
                    "local_processing_confirmed": True,
                },
            },
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 201, data)
        return json.loads(data)["run"]

    def upload_candidate_source(self, run, source_bytes):
        digest = hashlib.sha256(source_bytes).hexdigest()
        status, _, data = self.request(
            "PUT",
            f"/api/candidate-runs/{run['run_id']}/chunks/0",
            body=source_bytes,
            headers={
                **self.auth_headers(mutation=True),
                "Content-Type": "application/octet-stream",
                "Content-Range": f"bytes 0-{len(source_bytes) - 1}/{len(source_bytes)}",
                "X-Chunk-SHA256": digest,
            },
        )
        self.assertEqual(status, 200, data)
        return json.loads(data)["run"]

    def test_candidate_intake_requires_session_csrf_and_both_rights(self):
        payload = {
            "file": {
                "name": "video.mp4",
                "size_bytes": 10,
                "content_type": "video/mp4",
                "last_modified_ms": 0,
            },
            "rights": {
                "edit_analysis_confirmed": True,
                "local_processing_confirmed": True,
            },
        }
        status, _, _ = self.request("POST", "/api/candidate-runs", body=payload)
        self.assertEqual(status, 401)
        self.authenticate()
        status, _, _ = self.request(
            "POST",
            "/api/candidate-runs",
            body=payload,
            headers={**self.auth_headers(mutation=True), "X-CSRF-Token": "wrong"},
        )
        self.assertEqual(status, 403)
        payload["rights"]["edit_analysis_confirmed"] = False
        status, _, _ = self.request(
            "POST",
            "/api/candidate-runs",
            body=payload,
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 422)

    def test_candidate_upload_finalize_and_disk_backed_launch(self):
        self.authenticate()
        source = b"synthetic-media" * 100
        run = self.create_candidate_run(source)
        self.assertEqual(run["file"]["name"], "../../display-only.mp4")
        self.assertNotIn("rights", run)
        self.assertNotIn("run_dir", run)
        uploaded = self.upload_candidate_source(run, source)
        self.assertTrue(uploaded["upload"]["complete"])

        with patch(
            "short_factory.candidate_artifacts._probe_media",
            return_value={"duration_seconds": 60.0, "streams": ["audio", "video"]},
        ):
            status, _, data = self.request(
                "POST",
                f"/api/candidate-runs/{run['run_id']}/finalize",
                body={"size_bytes": len(source), "chunk_count": 1},
                headers=self.auth_headers(mutation=True),
            )
        self.assertEqual(status, 200, data)
        finalized = json.loads(data)["run"]
        self.assertTrue(finalized["source_ready"])
        self.assertEqual(finalized["status"], "finalized")

        status, _, data = self.request(
            "POST",
            f"/api/candidate-runs/{run['run_id']}/analyze",
            body={},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 202, data)
        self.assertEqual(self.candidate_launcher.calls, [run["run_id"]])
        self.assertEqual(json.loads(data)["run"]["status"], "queued")

        status, _, data = self.request(
            "GET",
            f"/api/candidate-runs/{run['run_id']}",
            headers=self.auth_headers(),
        )
        self.assertEqual(status, 200, data)
        self.assertEqual(json.loads(data)["run"]["status"], "queued")

    def test_candidate_chunk_rejects_wrong_hash_and_offset_without_progress(self):
        self.authenticate()
        source = b"source-bytes"
        run = self.create_candidate_run(source)
        for content_range, digest in (
            (f"bytes 1-{len(source)}/{len(source)}", hashlib.sha256(source).hexdigest()),
            (f"bytes 0-{len(source) - 1}/{len(source)}", "0" * 64),
        ):
            status, _, _ = self.request(
                "PUT",
                f"/api/candidate-runs/{run['run_id']}/chunks/0",
                body=source,
                headers={
                    **self.auth_headers(mutation=True),
                    "Content-Type": "application/octet-stream",
                    "Content-Range": content_range,
                    "X-Chunk-SHA256": digest,
                },
            )
            self.assertEqual(status, 422)
        status, _, data = self.request(
            "GET",
            f"/api/candidate-runs/{run['run_id']}",
            headers=self.auth_headers(),
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["run"]["upload"]["received_bytes"], 0)

    def test_candidate_preview_revalidates_hash_and_supports_range(self):
        self.authenticate()
        source = b"source" * 100
        run = self.create_candidate_run(source)
        self.upload_candidate_source(run, source)
        with patch(
            "short_factory.candidate_artifacts._probe_media",
            return_value={"duration_seconds": 60.0, "streams": ["audio", "video"]},
        ):
            status, _, data = self.request(
                "POST",
                f"/api/candidate-runs/{run['run_id']}/finalize",
                body={"size_bytes": len(source), "chunk_count": 1},
                headers=self.auth_headers(mutation=True),
            )
        self.assertEqual(status, 200, data)
        run_dir = self.server.candidate_root / run["run_id"]
        preview = run_dir / "work" / "candidate-001.mp4"
        preview.parent.mkdir()
        preview_bytes = b"0123456789abcdefghijklmnopqrstuvwxyz"
        preview.write_bytes(preview_bytes)
        document = {
            "schema_version": 1,
            "run_id": run["run_id"],
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "assessment": {"mode": "straight", "reason": "standalone"},
            "provider": "lmstudio",
            "model": "local-model",
            "prompt_version": "candidate-map-reduce-v2",
            "candidates": [
                {
                    "candidate_id": "candidate-001",
                    "rank": 1,
                    "start": 10.0,
                    "end": 50.0,
                    "duration": 40.0,
                    "hook": "hook",
                    "setup": "setup",
                    "payoff": "payoff",
                    "summary": "summary",
                    "reason": "reason",
                    "context_dependency": "low",
                    "risk": "low",
                    "mode": "straight",
                }
            ],
        }
        with patch(
            "short_factory.candidate_artifacts._probe_media",
            return_value={"duration_seconds": 40.0, "streams": ["audio", "video"]},
        ):
            published = publish_candidate_set(
                run_dir,
                document,
                preview_sources={"candidate-001": preview},
            )
        update_candidate_status(
            run_dir,
            state="complete",
            stage="complete",
            progress={"completed": 1, "total": 1},
            candidate_set_id=published["candidate_set_id"],
            candidate_count=1,
        )
        source_path = f"/api/candidate-runs/{run['run_id']}/source/video"
        status, headers, data = self.request(
            "GET", source_path, headers={**self.auth_headers(), "Range": "bytes=3-8"}
        )
        self.assertEqual(status, 206, data)
        self.assertEqual(data, source[3:9])
        self.assertEqual(headers["Content-Type"], "video/mp4")
        self.assertEqual(headers["Accept-Ranges"], "bytes")
        self.assertEqual(headers["ETag"], f'"{hashlib.sha256(source).hexdigest()}"')

        status, _, data = self.request(
            "POST",
            f"/api/candidate-runs/{run['run_id']}/adopt",
            body={"candidate_id": "candidate-001", "start": 8.5, "end": 52.25},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 202, data)
        self.assertEqual(
            self.launcher.calls[-1],
            ("adopt", run["run_id"], "candidate-001", 8.5, 52.25),
        )
        operation_url = json.loads(data)["status_url"]
        status, _, data = self.request("GET", operation_url, headers=self.auth_headers())
        self.assertEqual(status, 200, data)
        self.assertEqual(json.loads(data)["operation"]["result"]["job_id"], "clip-001-fixture")
        self.assertEqual(
            json.loads(data)["operation"]["result"]["project_id"],
            "clip-001-fixture",
        )

        for body in (
            {"candidate_id": "candidate-001", "start": -1, "end": 20},
            {"candidate_id": "candidate-001", "start": 20, "end": 20},
            {"candidate_id": "unknown", "start": 10, "end": 20},
        ):
            status, _, _ = self.request(
                "POST",
                f"/api/candidate-runs/{run['run_id']}/adopt",
                body=body,
                headers=self.auth_headers(mutation=True),
            )
            self.assertIn(status, {404, 422})
        path = f"/api/candidate-runs/{run['run_id']}/candidates/candidate-001/video"
        status, headers, data = self.request(
            "GET", path, headers={**self.auth_headers(), "Range": "bytes=2-7"}
        )
        self.assertEqual(status, 206, data)
        self.assertEqual(data, preview_bytes[2:8])
        self.assertEqual(headers["Content-Range"], f"bytes 2-7/{len(preview_bytes)}")
        self.assertEqual(headers["ETag"], f'"{hashlib.sha256(preview_bytes).hexdigest()}"')

        published_preview = (
            run_dir
            / "candidate-set"
            / published["candidate_set_id"]
            / "candidate-001.mp4"
        )
        published_preview.write_bytes(b"tampered")
        status, _, _ = self.request("GET", path, headers=self.auth_headers())
        self.assertEqual(status, 409)

    def test_candidate_path_traversal_never_resolves(self):
        self.authenticate()
        for path in (
            "/api/candidate-runs/%2e%2e",
            "/api/candidate-runs/..%5coutside",
            "/api/candidate-runs/C:%5csecret",
        ):
            status, _, _ = self.request("GET", path, headers=self.auth_headers())
            self.assertEqual(status, 404)

    def test_static_ui_has_security_headers_and_rejects_wrong_host(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Short Factory", body)
        self.assertIn(b"compositionCaptionOverviewList", body)
        self.assertIn(b"compositionCaptionAddButton", body)
        self.assertIn(b"compositionLiveCanvas", body)
        self.assertIn(b"compositionLiveSource", body)
        self.assertIn(b"compositionLiveSeek", body)
        self.assertNotIn(b"editorWorkspace", body)
        self.assertNotIn("字幕を編集".encode("utf-8"), body)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

        status, _, _ = self.request("GET", "/", headers={"Host": "evil.test"})
        self.assertEqual(status, 400)

    def test_static_live_preview_uses_text_content_without_mutation_requests(self):
        status, _, script = self.request("GET", "/assets/app.js")
        self.assertEqual(status, 200)
        source = script.decode("utf-8")
        self.assertIn('elements.liveCaptionText.textContent = active[0].text;', source)
        self.assertIn('requestVideoFrameCallback', source)
        self.assertNotIn('liveCaptionText.innerHTML', source)
        self.assertIn("preventing an old prefix from being combined", source)
        self.assertNotIn("nextCandidateChunkIndex", source)
        self.assertIn('candidateRunEndpoint("/adopt")', source)
        self.assertIn('apiRequest("/api/candidate-runs")', source)
        self.assertIn("source_video_url", source)
        self.assertNotIn("candidateList.innerHTML", source)
        self.assertIn("function rebuildCompositionLiveSegments", source)
        self.assertIn("function paintCompositionLiveFrame", source)
        self.assertIn("function renderCompositionCaptionOverview", source)
        self.assertIn("function addCompositionCaption", source)
        self.assertIn("function setCompositionCaptionBoundary", source)
        self.assertIn("advanceCompositionLiveSegment", source)
        self.assertIn("elements.compositionLiveSource.src = sourceUrl;", source)
        self.assertIn('placeholder.value = "live";', source)
        self.assertIn("format_start_time_num", source)

        composition_live_start = source.index("function compositionLiveTimeLabel")
        composition_live_end = source.index("async function loadCompositionProjects")
        composition_live_section = source[composition_live_start:composition_live_end]
        self.assertNotIn("apiRequest(", composition_live_section)
        self.assertNotIn("fetch(", composition_live_section)

        live_start = source.index("function activeCuesAt")
        live_end = source.index("function snapshotCues")
        live_section = source[live_start:live_end]
        self.assertNotIn("apiRequest(", live_section)
        self.assertNotIn("fetch(", live_section)

        status, _, stylesheet = self.request("GET", "/assets/style.css")
        self.assertEqual(status, 200)
        css = stylesheet.decode("utf-8")
        caption_style = css[
            css.index(".live-caption-text {") : css.index(".live-preview-badge {")
        ]
        self.assertIn("color: #fff", caption_style)
        self.assertIn("font-weight: 900", caption_style)
        self.assertIn("-webkit-text-stroke: 0", caption_style)
        self.assertNotIn("transform: scaleX", caption_style)

    def test_session_cookie_and_read_authentication(self):
        status, _, _ = self.request("GET", "/api/jobs")
        self.assertEqual(status, 401)

        status, _, _ = self.request(
            "POST",
            "/api/session",
            body={"launch_token": "launch-token-for-test"},
            headers={"Origin": "https://evil.test"},
        )
        self.assertEqual(status, 403)

        self.authenticate()
        status, headers, data = self.request(
            "GET", "/api/session", headers=self.auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["csrf_token"], self.csrf)
        self.assertIn("HttpOnly", self.cookie_header_from_new_session())
        self.assertIn("SameSite=Strict", self.cookie_header_from_new_session())

        status, _, _ = self.request(
            "POST",
            "/api/session",
            body={"launch_token": "雪"},
            headers={"Origin": self.origin},
        )
        self.assertEqual(status, 403)

    def cookie_header_from_new_session(self):
        status, headers, _ = self.request(
            "POST",
            "/api/session",
            body={"launch_token": "launch-token-for-test"},
            headers={"Origin": self.origin},
        )
        self.assertEqual(status, 200)
        return headers["Set-Cookie"]

    def test_read_endpoints_return_only_projected_artifacts(self):
        self.authenticate()
        headers = self.auth_headers()
        cases = [
            ("/api/jobs", "jobs"),
            ("/api/jobs/job1", "job"),
            ("/api/jobs/job1/captions/current", "caption"),
            ("/api/jobs/job1/captions/1", "caption"),
            ("/api/jobs/job1/renders/render1", "render"),
        ]
        for path, key in cases:
            with self.subTest(path=path):
                status, _, data = self.request("GET", path, headers=headers)
                self.assertEqual(status, 200, data)
                self.assertIn(key, json.loads(data))

        status, _, _ = self.request(
            "GET", "/api/jobs/%2e%2e/captions/current", headers=headers
        )
        self.assertEqual(status, 404)

        status, _, data = self.request("GET", "/api/jobs/job1", headers=headers)
        self.assertEqual(status, 200, data)
        projected = json.loads(data)["job"]
        self.assertAlmostEqual(projected["caption_minimum_seconds"], 0.65)
        self.assertEqual(projected["caption_max_chars_per_line"], 15)
        self.assertEqual(projected["caption_max_lines"], 2)
        self.assertNotIn("config", projected)

    def test_jobs_listing_does_not_follow_directory_symlink(self):
        outside = Path(self.temporary.name) / "escape"
        outside.mkdir()
        (outside / "job.json").write_text(
            json.dumps({"version": 3, "job_id": "escape", "duration_seconds": 1.0}),
            encoding="utf-8",
        )
        initialize_machine_revision(
            outside, [{"start": 0.0, "end": 1.0, "text": "outside"}]
        )
        link = self.jobs_root / "escape"
        try:
            create_directory_link(link, outside)
        except OSError as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        try:
            self.authenticate()
            status, _, data = self.request(
                "GET", "/api/jobs", headers=self.auth_headers()
            )
            self.assertEqual(status, 200)
            ids = [item["job_id"] for item in json.loads(data)["jobs"]]
            self.assertNotIn("escape", ids)
        finally:
            os.rmdir(link)

    def test_malformed_job_shape_does_not_break_jobs_listing(self):
        malformed = self.jobs_root / "malformed"
        malformed.mkdir()
        (malformed / "job.json").write_text("[]", encoding="utf-8")
        self.authenticate()
        status, _, data = self.request("GET", "/api/jobs", headers=self.auth_headers())
        self.assertEqual(status, 200)
        ids = [item["job_id"] for item in json.loads(data)["jobs"]]
        self.assertEqual(ids, ["job1"])

    def test_caption_save_accepts_text_only_and_exposes_operation_status(self):
        self.authenticate()
        cues = [dict(cue) for cue in self.caption["cues"]]
        cues[0]["text"] = "修正した字幕"
        status, headers, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": cues},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 202, data)
        payload = json.loads(data)
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(headers["Location"], payload["status_url"])
        self.assertEqual(self.launcher.calls[0][0:2], ("save", "job1"))
        self.assertEqual(self.launcher.calls[0][2]["cues"][0]["text"], "修正した字幕")

        status, _, data = self.request(
            "GET", payload["status_url"], headers=self.auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["operation"]["result"]["revision"], 2)

    def test_caption_save_accepts_timing_and_new_cue_without_client_id(self):
        self.authenticate()
        cues = [dict(self.caption["cues"][0])]
        cues[0]["end"] = 0.7
        cues.append({"id": None, "start": 0.7, "end": 1.4, "text": "追加字幕"})
        second = dict(self.caption["cues"][1])
        second["start"] = 1.4
        cues.append(second)

        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": cues},
            headers=self.auth_headers(mutation=True),
        )

        self.assertEqual(status, 202, data)
        submitted = self.launcher.calls[-1][2]["cues"]
        self.assertIsNone(submitted[1]["id"])
        self.assertEqual(submitted[0]["end"], 0.7)
        self.assertEqual(submitted[2]["start"], 1.4)

    def test_caption_save_rejects_stale_base_before_worker_launch(self):
        self.authenticate()
        cues = [dict(cue) for cue in self.caption["cues"]]
        cues[0]["text"] = "stale edit"
        before = list(self.launcher.calls)

        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 2, "cues": cues},
            headers=self.auth_headers(mutation=True),
        )

        self.assertEqual(status, 409, data)
        self.assertEqual(json.loads(data)["error"]["code"], "revision_conflict")
        self.assertEqual(self.launcher.calls, before)

    def test_caption_save_rejects_csrf(self):
        self.authenticate()
        cues = [dict(cue) for cue in self.caption["cues"]]
        cues[0]["text"] = "修正"
        status, _, _ = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": cues},
            headers=self.auth_headers(),
        )
        self.assertEqual(status, 403)

        status, _, _ = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": cues},
            headers={
                "Cookie": self.cookie,
                "Origin": self.origin,
                "X-CSRF-Token": "é",
            },
        )
        self.assertEqual(status, 403)

    def test_caption_save_rejects_invalid_identity_and_payload_shape(self):
        self.authenticate()
        current = [dict(cue) for cue in self.caption["cues"]]

        unknown = [dict(cue) for cue in current]
        unknown[0]["id"] = "caller-created-id"
        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": unknown},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 422, data)
        self.assertEqual(json.loads(data)["error"]["code"], "unknown_cue_id")

        deleted = [dict(current[0])]
        deleted[0]["text"] = "変更"
        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": deleted},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 422, data)
        self.assertEqual(
            json.loads(data)["error"]["code"], "cue_deletion_forbidden"
        )

        reordered = [dict(cue) for cue in current]
        reordered[0]["id"], reordered[1]["id"] = (
            reordered[1]["id"],
            reordered[0]["id"],
        )
        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": reordered},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 422, data)
        self.assertEqual(json.loads(data)["error"]["code"], "cue_reorder_forbidden")

        duplicated = [dict(cue) for cue in current]
        duplicated[1]["id"] = duplicated[0]["id"]
        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": duplicated},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 422, data)
        self.assertEqual(json.loads(data)["error"]["code"], "duplicate_cue_id")

        status, _, _ = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "operations": [{"op": "split"}]},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 400)

        extra = [dict(cue) for cue in current]
        extra[0]["extra"] = True
        status, _, data = self.request(
            "PUT",
            "/api/jobs/job1/captions",
            body={"base_revision": 1, "cues": extra},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 422, data)
        self.assertEqual(json.loads(data)["error"]["code"], "invalid_cue")

    def test_caption_save_rejects_invalid_timing_and_full_noop(self):
        self.authenticate()
        current = [dict(cue) for cue in self.caption["cues"]]
        cases = []

        overlap = [dict(cue) for cue in current]
        overlap[1]["start"] = 1.199
        cases.append(("overlapping_cues", overlap))

        nonfinite = [dict(cue) for cue in current]
        nonfinite[0]["start"] = float("nan")
        cases.append(("invalid_timing", nonfinite))

        rounded_negative = [dict(cue) for cue in current]
        rounded_negative[0]["start"] = -0.0001
        cases.append(("invalid_timing", rounded_negative))

        rounded_past_end = [dict(cue) for cue in current]
        rounded_past_end[-1]["end"] = 2.4001
        cases.append(("invalid_timing", rounded_past_end))

        too_short = [dict(cue) for cue in current]
        too_short[0]["end"] = 0.649
        cases.append(("cue_too_short", too_short))

        cases.append(("no_changes", current))
        for expected, cues in cases:
            with self.subTest(expected=expected):
                status, _, data = self.request(
                    "PUT",
                    "/api/jobs/job1/captions",
                    body={"base_revision": 1, "cues": cues},
                    headers=self.auth_headers(mutation=True),
                )
                self.assertEqual(status, 422, data)
                self.assertEqual(json.loads(data)["error"]["code"], expected)

    def test_caption_save_rejects_render_invalid_line_layout(self):
        self.authenticate()
        cases = []
        too_long = [dict(cue) for cue in self.caption["cues"]]
        too_long[0]["text"] = "1234567890123456"
        cases.append(("line_too_long", too_long))
        too_many = [dict(cue) for cue in self.caption["cues"]]
        too_many[0]["text"] = "一\n二\n三"
        cases.append(("too_many_lines", too_many))

        for expected, cues in cases:
            with self.subTest(expected=expected):
                status, _, data = self.request(
                    "PUT",
                    "/api/jobs/job1/captions",
                    body={"base_revision": 1, "cues": cues},
                    headers=self.auth_headers(mutation=True),
                )
                self.assertEqual(status, 422, data)
                self.assertEqual(json.loads(data)["error"]["code"], expected)

    def test_render_launcher_requires_explicit_revision(self):
        self.authenticate()
        status, _, data = self.request(
            "POST",
            "/api/jobs/job1/renders",
            body={"caption_revision": 1},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 202, data)
        self.assertEqual(self.launcher.calls[-1], ("render", "job1", 1))

        status, _, _ = self.request(
            "POST",
            "/api/jobs/job1/renders",
            body={"caption_revision": 1, "current": True},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 400)

    def test_video_range_suffix_if_range_and_head(self):
        self.authenticate()
        headers = self.auth_headers()
        headers["Range"] = "bytes=2-5"
        status, response_headers, data = self.request(
            "GET", "/api/jobs/job1/renders/render1/video", headers=headers
        )
        self.assertEqual(status, 206)
        self.assertEqual(data, self.video_bytes[2:6])
        self.assertEqual(
            response_headers["Content-Range"], f"bytes 2-5/{len(self.video_bytes)}"
        )
        self.assertEqual(response_headers["Accept-Ranges"], "bytes")
        self.assertEqual(response_headers["ETag"], f'"{self.output_hash}"')

        suffix_headers = self.auth_headers()
        suffix_headers["Range"] = "bytes=-4"
        status, _, data = self.request(
            "GET", "/api/jobs/job1/renders/render1/video", headers=suffix_headers
        )
        self.assertEqual(status, 206)
        self.assertEqual(data, self.video_bytes[-4:])

        full_headers = self.auth_headers()
        full_headers.update({"Range": "bytes=2-5", "If-Range": '"different"'})
        status, _, data = self.request(
            "GET", "/api/jobs/job1/renders/render1/video", headers=full_headers
        )
        self.assertEqual(status, 200)
        self.assertEqual(data, self.video_bytes)

        status, head_headers, data = self.request(
            "HEAD",
            "/api/jobs/job1/renders/render1/video",
            headers={**self.auth_headers(), "Range": "bytes=0-3"},
        )
        self.assertEqual(status, 206)
        self.assertEqual(data, b"")
        self.assertEqual(head_headers["Content-Length"], "4")

    def test_invalid_or_multiple_range_returns_416(self):
        self.authenticate()
        for value in (
            "bytes=999-1000",
            "bytes=0-1,3-4",
            "items=0-1",
            "bytes=-0",
            "bytes=" + "9" * 5000 + "-",
        ):
            with self.subTest(value=value):
                status, headers, _ = self.request(
                    "GET",
                    "/api/jobs/job1/renders/render1/video",
                    headers={**self.auth_headers(), "Range": value},
                )
                self.assertEqual(status, 416)
                self.assertEqual(
                    headers["Content-Range"], f"bytes */{len(self.video_bytes)}"
                )

    def test_tampered_video_is_never_streamed(self):
        self.authenticate()
        self.video_path.write_bytes(b"tampered")
        status, _, data = self.request(
            "GET",
            "/api/jobs/job1/renders/render1/video",
            headers=self.auth_headers(),
        )
        self.assertEqual(status, 409)
        self.assertNotEqual(data, b"tampered")

    def test_default_launcher_uses_fixed_argv_and_shell_false(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = None
                self.stdout = io.StringIO("BUSY\n")
                self.stderr = io.StringIO("")

            def wait(self):
                return 0

            def terminate(self):
                return None

        launcher = review_server.MutationLauncher(
            self.jobs_root, python_executable="python-test"
        )
        with patch.object(
            review_server.subprocess, "Popen", return_value=FakeProcess()
        ) as popen:
            outcome = launcher.launch_render("job1", 7)
        self.assertEqual(outcome.state, "BUSY")
        command = popen.call_args.args[0]
        self.assertEqual(
            command,
            [
                "python-test",
                "-m",
                "short_factory",
                "render-job",
                "--jobs-root",
                str(self.jobs_root.resolve()),
                "--job-id",
                "job1",
                "--caption-revision",
                "7",
            ],
        )
        self.assertIs(popen.call_args.kwargs["shell"], False)

    def test_candidate_adopt_launcher_uses_fixed_server_paths_and_numeric_range(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = None
                self.stdout = io.StringIO("BUSY\n")
                self.stderr = io.StringIO("")

            def wait(self):
                return 0

            def terminate(self):
                return None

        launcher = review_server.MutationLauncher(
            self.jobs_root, python_executable="python-test"
        )
        with patch.object(
            review_server.subprocess, "Popen", return_value=FakeProcess()
        ) as popen:
            outcome = launcher.launch_candidate_adopt(
                "candidate-run1", "candidate-001", 12.3454, 56.7894
            )
        self.assertEqual(outcome.state, "BUSY")
        self.assertEqual(
            popen.call_args.args[0],
            [
                "python-test",
                "-m",
                "short_factory",
                "adopt-candidate-range",
                "--jobs-root",
                str(self.jobs_root.resolve()),
                "--candidate-root",
                str(self.jobs_root.resolve() / ".candidate-runs"),
                "--composition-projects-root",
                str(self.jobs_root.resolve().parent / "composition-projects"),
                "--run-id",
                "candidate-run1",
                "--candidate-id",
                "candidate-001",
                "--start",
                "12.345",
                "--end",
                "56.789",
            ],
        )
        self.assertIs(popen.call_args.kwargs["shell"], False)

    def test_default_launcher_records_only_safe_completion_result(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = None
                self.stdout = io.StringIO(
                    'LOCK_ACQUIRED\n{"ok":true,"result":{"render_id":"render2"}}\n'
                )
                self.stderr = io.StringIO("sensitive worker detail\n")

            def wait(self):
                return 0

            def terminate(self):
                return None

        launcher = review_server.MutationLauncher(
            self.jobs_root, python_executable="python-test"
        )
        with patch.object(
            review_server.subprocess, "Popen", return_value=FakeProcess()
        ):
            outcome = launcher.launch_render("job1", 1)
        self.assertEqual(outcome.state, "LOCK_ACQUIRED")
        self.assertIsNotNone(outcome.operation_id)
        deadline = time.monotonic() + 1
        operation = launcher.get_status(outcome.operation_id)
        while operation and operation["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.01)
            operation = launcher.get_status(outcome.operation_id)
        self.assertEqual(
            operation,
            {"status": "complete", "result": {"render_id": "render2"}},
        )

    def test_launcher_maps_worker_failures_to_safe_operation_errors(self):
        cases = (
            (
                '{"ok":false,"status":409,"error":"sensitive stale path"}',
                3,
                {
                    "code": "revision_conflict",
                    "message": "Revision changed. Existing artifacts were kept.",
                },
            ),
            (
                '{"ok":false,"status":422,"error":"sensitive validation detail"}',
                1,
                {
                    "code": "operation_failed",
                    "message": "Operation failed. Existing artifacts were kept.",
                },
            ),
        )
        for final_line, return_code, expected_error in cases:
            with self.subTest(expected=expected_error["code"]):
                class FakeProcess:
                    def __init__(self):
                        self.stdin = None
                        self.stdout = io.StringIO(
                            "LOCK_ACQUIRED\n" + final_line + "\n"
                        )
                        self.stderr = io.StringIO("sensitive stderr detail\n")

                    def wait(self):
                        return return_code

                    def terminate(self):
                        return None

                launcher = review_server.MutationLauncher(
                    self.jobs_root, python_executable="python-test"
                )
                with patch.object(
                    review_server.subprocess, "Popen", return_value=FakeProcess()
                ):
                    outcome = launcher.launch_render("job1", 1)
                self.assertEqual(outcome.state, "LOCK_ACQUIRED")
                deadline = time.monotonic() + 1
                operation = launcher.get_status(outcome.operation_id)
                while (
                    operation
                    and operation["status"] == "running"
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.01)
                    operation = launcher.get_status(outcome.operation_id)
                self.assertEqual(
                    operation,
                    {"status": "failed", "error": expected_error},
                )
                projected = json.dumps(operation, ensure_ascii=False)
                self.assertNotIn("sensitive", projected)
                self.assertNotIn("path", projected)

    def test_launcher_stdin_and_first_line_wait_share_one_bound(self):
        release = threading.Event()

        class BlockingInput:
            def write(self, _value):
                release.wait(2)

            def close(self):
                return None

        class BlockingOutput:
            def readline(self):
                release.wait(2)
                return ""

            def __iter__(self):
                return iter(())

        class FakeProcess:
            def __init__(self):
                self.stdin = BlockingInput()
                self.stdout = BlockingOutput()
                self.stderr = io.StringIO("")
                self.terminated = False

            def wait(self, timeout=None):
                return 1

            def terminate(self):
                self.terminated = True
                release.set()

            def kill(self):
                release.set()

        process = FakeProcess()
        launcher = review_server.MutationLauncher(
            self.jobs_root,
            python_executable="python-test",
            startup_timeout=0.05,
        )
        started = time.monotonic()
        with patch.object(review_server.subprocess, "Popen", return_value=process):
            outcome = launcher.launch_save("job1", {"base_revision": 1, "cues": []})
        elapsed = time.monotonic() - started
        self.assertEqual(outcome.state, "ERROR")
        self.assertTrue(process.terminated)
        self.assertLess(elapsed, 0.5)

    def test_unknown_worker_marker_is_terminated_and_untracked(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = None
                self.stdout = io.StringIO("noise\nLOCK_ACQUIRED\n")
                self.stderr = io.StringIO("")
                self.terminated = False

            def wait(self, timeout=None):
                return 1

            def terminate(self):
                self.terminated = True

            def kill(self):
                self.terminated = True

        process = FakeProcess()
        launcher = review_server.MutationLauncher(
            self.jobs_root, python_executable="python-test"
        )
        with patch.object(review_server.subprocess, "Popen", return_value=process):
            outcome = launcher.launch_render("job1", 1)
        self.assertEqual(outcome.state, "ERROR")
        self.assertTrue(process.terminated)
        self.assertEqual(launcher.operations, {})

    def test_lock_marker_with_extra_text_is_rejected(self):
        class FakeProcess:
            def __init__(self):
                self.stdin = None
                self.stdout = io.StringIO("LOCK_ACQUIRED unexpected\n")
                self.stderr = io.StringIO("")
                self.terminated = False

            def wait(self, timeout=None):
                return 1

            def terminate(self):
                self.terminated = True

            def kill(self):
                self.terminated = True

        process = FakeProcess()
        launcher = review_server.MutationLauncher(
            self.jobs_root, python_executable="python-test"
        )
        with patch.object(review_server.subprocess, "Popen", return_value=process):
            outcome = launcher.launch_render("job1", 1)
        self.assertEqual(outcome.state, "ERROR")
        self.assertTrue(process.terminated)
        self.assertEqual(launcher.operations, {})

    def test_composition_review_routes_project_source_and_mutations(self):
        self.authenticate()
        status, _, data = self.request(
            "GET", "/api/compositions", headers=self.auth_headers()
        )
        self.assertEqual(status, 200, data)
        projects = json.loads(data)["projects"]
        self.assertEqual(projects[0]["project_id"], "composition1")
        self.assertEqual(projects[0]["current_revision"], 1)

        status, _, data = self.request(
            "GET", "/api/compositions/composition1", headers=self.auth_headers()
        )
        self.assertEqual(status, 200, data)
        composition = json.loads(data)["composition"]
        self.assertEqual(composition["edit"]["revision"], 1)
        self.assertEqual(composition["source"]["width"], 1920)
        self.assertEqual(composition["source"]["format_start_time_num"], 0)
        self.assertEqual(composition["source"]["format_start_time_den"], 1)
        self.assertNotIn("path", composition["source"])

        status, headers, data = self.request(
            "GET",
            "/api/compositions/composition1/source/video",
            headers={**self.auth_headers(), "Range": "bytes=0-10"},
        )
        self.assertEqual(status, 206, data)
        self.assertEqual(data, self.composition_source.read_bytes()[:11])
        self.assertEqual(headers["Accept-Ranges"], "bytes")

        plan = load_current_edit(self.composition_root / "composition1")["plan"]
        plan["speech_captions"][0]["text"] = "UIから修正"
        status, _, _ = self.request(
            "PUT",
            "/api/compositions/composition1/edits",
            body={"base_revision": 1, "plan": plan},
            headers=self.auth_headers(),
        )
        self.assertEqual(status, 403)
        status, _, data = self.request(
            "PUT",
            "/api/compositions/composition1/edits",
            body={"base_revision": 1, "plan": plan},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 202, data)
        self.assertEqual(self.launcher.calls[-1][0], "composition-save")

        status, _, data = self.request(
            "POST",
            "/api/compositions/composition1/renders",
            body={"edit_revision": 1, "profile": "proxy"},
            headers=self.auth_headers(mutation=True),
        )
        self.assertEqual(status, 202, data)
        self.assertEqual(self.launcher.calls[-1][0], "composition-render")


if __name__ == "__main__":
    unittest.main()
