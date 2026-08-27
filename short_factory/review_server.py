from __future__ import annotations

import hmac
import http.cookies
import json
import math
import os
import queue
import re
import secrets
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .artifacts import (
    ConflictError,
    NotFoundError,
    ValidationError,
    WorkflowError,
    caption_duration_floor,
    caption_layout_limits,
    confined_job_path,
    ensure_workflow_job,
    list_workflow_jobs,
    load_caption_revision,
    load_current_caption,
    load_render,
    project_job,
    safe_job_dir,
)
from .candidate_artifacts import (
    UPLOAD_CHUNK_BYTES,
    CandidateArtifactError,
    CandidateConflictError,
    CandidateNotFoundError,
    append_upload_chunk,
    candidate_preview,
    candidate_source,
    create_candidate_run,
    finalize_upload,
    list_candidate_runs,
    load_run as load_candidate_run,
    prepare_analysis,
    project_candidate_run,
    request_cancel,
    update_status as update_candidate_status,
)
from .composition_artifacts import (
    composition_source_for_review,
    confined_composition_path,
    list_composition_projects,
    load_composition_render,
    project_composition_for_review,
    safe_composition_project_dir,
)


LOOPBACK_HOST = "127.0.0.1"
SESSION_COOKIE = "short_factory_review_session"
MAX_JSON_BYTES = 256 * 1024
STREAM_CHUNK_BYTES = 512 * 1024
SAFE_ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}"
SAFE_ID = re.compile(rf"\A{SAFE_ID_PATTERN}\Z")
SAFE_CUE_ID = SAFE_ID
SHA256 = re.compile(r"\A(?:sha256:)?[0-9a-fA-F]{64}\Z")

JOB_ROUTE = re.compile(rf"\A/api/jobs/({SAFE_ID_PATTERN})\Z")
CURRENT_CAPTION_ROUTE = re.compile(
    rf"\A/api/jobs/({SAFE_ID_PATTERN})/captions/current\Z"
)
CAPTION_ROUTE = re.compile(
    rf"\A/api/jobs/({SAFE_ID_PATTERN})/captions/([1-9][0-9]{{0,8}})\Z"
)
CAPTION_SAVE_ROUTE = re.compile(rf"\A/api/jobs/({SAFE_ID_PATTERN})/captions\Z")
RENDER_CREATE_ROUTE = re.compile(rf"\A/api/jobs/({SAFE_ID_PATTERN})/renders\Z")
RENDER_ROUTE = re.compile(
    rf"\A/api/jobs/({SAFE_ID_PATTERN})/renders/({SAFE_ID_PATTERN})\Z"
)
VIDEO_ROUTE = re.compile(
    rf"\A/api/jobs/({SAFE_ID_PATTERN})/renders/({SAFE_ID_PATTERN})/video\Z"
)
OPERATION_ROUTE = re.compile(r"\A/api/operations/([A-Za-z0-9_-]{16,128})\Z")
CANDIDATE_RUNS_ROUTE = "/api/candidate-runs"
CANDIDATE_RUN_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})\Z"
)
CANDIDATE_CHUNK_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/chunks/([0-9]{{1,8}})\Z"
)
CANDIDATE_FINALIZE_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/finalize\Z"
)
CANDIDATE_ANALYZE_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/(analyze|resume)\Z"
)
CANDIDATE_CANCEL_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/cancel\Z"
)
CANDIDATE_VIDEO_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/candidates/({SAFE_ID_PATTERN})/video\Z"
)
CANDIDATE_SOURCE_VIDEO_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/source/video\Z"
)
CANDIDATE_ADOPT_ROUTE = re.compile(
    rf"\A/api/candidate-runs/({SAFE_ID_PATTERN})/adopt\Z"
)
COMPOSITION_PROJECTS_ROUTE = "/api/compositions"
COMPOSITION_PROJECT_ROUTE = re.compile(
    rf"\A/api/compositions/({SAFE_ID_PATTERN})\Z"
)
COMPOSITION_EDIT_ROUTE = re.compile(
    rf"\A/api/compositions/({SAFE_ID_PATTERN})/edits\Z"
)
COMPOSITION_RENDER_CREATE_ROUTE = re.compile(
    rf"\A/api/compositions/({SAFE_ID_PATTERN})/renders\Z"
)
COMPOSITION_VIDEO_ROUTE = re.compile(
    rf"\A/api/compositions/({SAFE_ID_PATTERN})/renders/({SAFE_ID_PATTERN})/video\Z"
)
COMPOSITION_SOURCE_VIDEO_ROUTE = re.compile(
    rf"\A/api/compositions/({SAFE_ID_PATTERN})/source/video\Z"
)

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/assets/style.css": ("style.css", "text/css; charset=utf-8"),
}

CSP = (
    "default-src 'none'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "media-src 'self'; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'; "
    "object-src 'none'"
)


class RequestError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class RangeError(Exception):
    pass


def _bounded_ascii(value: Any, *, maximum: int) -> bool:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        return False
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _bounded_ascii_equal(supplied: Any, expected: Any) -> bool:
    if not _bounded_ascii(supplied, maximum=256) or not _bounded_ascii(
        expected, maximum=256
    ):
        return False
    return hmac.compare_digest(supplied.encode("ascii"), expected.encode("ascii"))


def _startup_marker(line: str) -> str:
    value = line.strip()
    if value in {"LOCK_ACQUIRED", "BUSY"}:
        return value
    if value.startswith("ERROR "):
        try:
            payload = json.loads(value[6:])
        except json.JSONDecodeError:
            return ""
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            return "ERROR"
    return ""


@dataclass(frozen=True)
class LaunchOutcome:
    state: str
    operation_id: str | None = None


class MutationLauncher:
    """Launch the lock-owning CLI and wait only for its startup result."""

    def __init__(
        self,
        jobs_root: Path,
        *,
        composition_projects_root: Path | None = None,
        python_executable: str | Path | None = None,
        startup_timeout: float = 8.0,
    ):
        self.jobs_root = jobs_root.resolve()
        self.composition_projects_root = (
            composition_projects_root.expanduser().resolve()
            if composition_projects_root is not None
            else (self.jobs_root.parent / "composition-projects").resolve()
        )
        self.python_executable = str(python_executable or sys.executable)
        self.startup_timeout = startup_timeout
        self.operations: dict[str, dict[str, Any]] = {}
        self.operations_lock = threading.Lock()

    def get_status(self, operation_id: str) -> dict[str, Any] | None:
        with self.operations_lock:
            value = self.operations.get(operation_id)
            return dict(value) if value is not None else None

    def _set_status(self, operation_id: str, value: dict[str, Any]) -> None:
        with self.operations_lock:
            self.operations[operation_id] = value
            if len(self.operations) > 128:
                for old_id, old_value in list(self.operations.items()):
                    if old_id != operation_id and old_value.get("status") != "running":
                        self.operations.pop(old_id, None)
                        break

    def launch_save(self, job_id: str, payload: dict[str, Any]) -> LaunchOutcome:
        command = [
            self.python_executable,
            "-m",
            "short_factory",
            "save-captions",
            "--jobs-root",
            str(self.jobs_root),
            "--job-id",
            job_id,
            "--stdin-json",
        ]
        stdin_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return self._launch(
            command,
            stdin_text,
            conflict_message="Caption revision changed. Your draft was kept.",
        )

    def launch_render(self, job_id: str, caption_revision: int) -> LaunchOutcome:
        command = [
            self.python_executable,
            "-m",
            "short_factory",
            "render-job",
            "--jobs-root",
            str(self.jobs_root),
            "--job-id",
            job_id,
            "--caption-revision",
            str(caption_revision),
        ]
        return self._launch(command, None)

    def launch_candidate_adopt(
        self,
        run_id: str,
        candidate_id: str,
        start: float,
        end: float,
    ) -> LaunchOutcome:
        command = [
            self.python_executable,
            "-m",
            "short_factory",
            "adopt-candidate-range",
            "--jobs-root",
            str(self.jobs_root),
            "--candidate-root",
            str(self.jobs_root / ".candidate-runs"),
            "--composition-projects-root",
            str(self.composition_projects_root),
            "--run-id",
            run_id,
            "--candidate-id",
            candidate_id,
            "--start",
            f"{start:.3f}",
            "--end",
            f"{end:.3f}",
        ]
        return self._launch(command, None)

    def launch_composition_save(
        self,
        projects_root: Path,
        project_id: str,
        payload: dict[str, Any],
    ) -> LaunchOutcome:
        command = [
            self.python_executable,
            "-m",
            "short_factory",
            "composition-save-worker",
            "--projects-root",
            str(projects_root),
            "--project-id",
            project_id,
        ]
        stdin_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return self._launch(
            command,
            stdin_text,
            conflict_message="Composition revision changed. Your draft was kept.",
        )

    def launch_composition_render(
        self,
        projects_root: Path,
        project_id: str,
        edit_revision: int,
        render_profile: str,
    ) -> LaunchOutcome:
        command = [
            self.python_executable,
            "-m",
            "short_factory",
            "composition-render-worker",
            "--projects-root",
            str(projects_root),
            "--project-id",
            project_id,
            "--edit-revision",
            str(edit_revision),
            "--profile",
            render_profile,
        ]
        return self._launch(command, None)

    def _launch(
        self,
        command: list[str],
        stdin_text: str | None,
        *,
        conflict_message: str = "Revision changed. Existing artifacts were kept.",
    ) -> LaunchOutcome:
        operation_id = secrets.token_urlsafe(18)
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                creationflags=creationflags,
            )
        except OSError:
            return LaunchOutcome("ERROR")

        first_line: queue.Queue[str] = queue.Queue(maxsize=1)

        def drain_stdout() -> None:
            assert process.stdout is not None
            line = process.stdout.readline()
            marker = _startup_marker(line)
            if marker == "LOCK_ACQUIRED":
                self._set_status(operation_id, {"status": "running"})
            try:
                first_line.put_nowait(line)
            except queue.Full:
                pass
            final_line = ""
            for output_line in process.stdout:
                if output_line.strip():
                    final_line = output_line.strip()
            return_code = process.wait()
            if marker != "LOCK_ACQUIRED":
                return
            try:
                completion = json.loads(final_line)
            except (json.JSONDecodeError, TypeError):
                completion = None
            if (
                return_code == 0
                and isinstance(completion, dict)
                and completion.get("ok") is True
                and isinstance(completion.get("result"), dict)
            ):
                self._set_status(
                    operation_id,
                    {"status": "complete", "result": completion["result"]},
                )
            else:
                error = {
                    "code": "operation_failed",
                    "message": "Operation failed. Existing artifacts were kept.",
                }
                if (
                    isinstance(completion, dict)
                    and completion.get("ok") is False
                    and completion.get("status") == 409
                ):
                    error = {
                        "code": "revision_conflict",
                        "message": conflict_message,
                    }
                self._set_status(
                    operation_id,
                    {"status": "failed", "error": error},
                )

        def drain_stderr() -> None:
            assert process.stderr is not None
            for _ in process.stderr:
                pass

        def write_stdin() -> None:
            if stdin_text is None or process.stdin is None:
                return
            try:
                process.stdin.write(stdin_text)
                process.stdin.close()
            except (BrokenPipeError, OSError, ValueError):
                self._terminate_and_reap(process)

        threading.Thread(target=drain_stdout, daemon=True).start()
        threading.Thread(target=drain_stderr, daemon=True).start()
        threading.Thread(target=write_stdin, daemon=True).start()

        try:
            marker_line = first_line.get(timeout=self.startup_timeout)
        except queue.Empty:
            self._terminate_and_reap(process)
            self._set_status(operation_id, {"status": "failed"})
            return LaunchOutcome("ERROR")

        marker = _startup_marker(marker_line)
        if marker == "LOCK_ACQUIRED":
            return LaunchOutcome(marker, operation_id)
        if marker in {"BUSY", "ERROR"}:
            self._terminate_and_reap(process)
            return LaunchOutcome(marker)
        self._terminate_and_reap(process)
        return LaunchOutcome("ERROR")

    @staticmethod
    def _terminate_and_reap(process: subprocess.Popen[str]) -> None:
        try:
            process.terminate()
        except (OSError, ProcessLookupError):
            pass
        try:
            process.wait(timeout=1.0)
        except TypeError:
            # Test doubles and older process-like adapters may not accept timeout.
            process.wait()
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (AttributeError, OSError, ProcessLookupError):
                pass
            try:
                process.wait(timeout=1.0)
            except (TypeError, subprocess.TimeoutExpired):
                pass


class CandidateLauncher:
    """Start a disk-reporting candidate worker without waiting for completion."""

    def __init__(
        self,
        candidate_root: Path,
        *,
        python_executable: str | Path | None = None,
        config_path: Path | None = None,
    ):
        self.candidate_root = candidate_root.expanduser().absolute()
        self.python_executable = str(python_executable or sys.executable)
        self.config_path = (
            config_path
            or Path(__file__).resolve().parent.parent
            / "config"
            / "candidates"
            / "default.json"
        ).resolve()

    def launch(self, run_id: str) -> bool:
        command = [
            self.python_executable,
            "-m",
            "short_factory",
            "candidate-worker",
            "--candidate-root",
            str(self.candidate_root),
            "--run-id",
            run_id,
            "--config",
            str(self.config_path),
        ]
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        try:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(Path(__file__).resolve().parent.parent),
                shell=False,
                creationflags=creationflags,
                close_fds=True,
            )
        except OSError:
            return False
        return True


class ReviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        jobs_root: Path,
        port: int,
        *,
        composition_projects_root: Path | None = None,
        launch_token: str | None = None,
        launcher: Any | None = None,
        candidate_launcher: Any | None = None,
        python_executable: str | Path | None = None,
    ):
        root = jobs_root.expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"jobs root does not exist: {root}")
        self.jobs_root = root
        self.launch_token = launch_token or secrets.token_urlsafe(32)
        if not _bounded_ascii(self.launch_token, maximum=256):
            raise ValueError("launch token must be bounded ASCII text")
        self.sessions: dict[str, str] = {}
        self.sessions_lock = threading.Lock()
        self.webui_root = Path(__file__).resolve().with_name("webui")
        self.candidate_root = root / ".candidate-runs"
        self.composition_projects_root = (
            composition_projects_root.expanduser().resolve()
            if composition_projects_root is not None
            else (root.parent / "composition-projects").resolve()
        )
        self.mutation_launcher = launcher or MutationLauncher(
            root,
            composition_projects_root=self.composition_projects_root,
            python_executable=python_executable,
        )
        self.candidate_launcher = candidate_launcher or CandidateLauncher(
            self.candidate_root, python_executable=python_executable
        )
        super().__init__((LOOPBACK_HOST, port), ReviewRequestHandler)
        actual_port = int(self.server_address[1])
        self.expected_host = f"{LOOPBACK_HOST}:{actual_port}"
        self.origin = f"http://{self.expected_host}"

    @property
    def launch_url(self) -> str:
        return f"{self.origin}/#token={self.launch_token}"

    def create_session(self) -> tuple[str, str]:
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        with self.sessions_lock:
            self.sessions[session_id] = csrf_token
        return session_id, csrf_token

    def get_csrf(self, session_id: str) -> str | None:
        with self.sessions_lock:
            return self.sessions.get(session_id)


class ReviewRequestHandler(BaseHTTPRequestHandler):
    server: ReviewHTTPServer
    server_version = "ClientShortFactoryReview/1"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # Do not log tokens, source paths, request bodies, or media identifiers.
        return

    def do_GET(self) -> None:
        if not self._valid_host():
            return
        path = self._request_path()
        if path is None:
            return
        if path in STATIC_FILES:
            self._serve_static(path, head_only=False)
            return
        if path == "/api/session":
            session = self._require_session()
            if session is not None:
                self._send_json(200, {"csrf_token": session[1]})
            return
        session = self._require_session()
        if session is None:
            return
        self._dispatch_get(path, head_only=False)

    def do_HEAD(self) -> None:
        if not self._valid_host():
            return
        path = self._request_path()
        if path is None:
            return
        if path in STATIC_FILES:
            self._serve_static(path, head_only=True)
            return
        if self._require_session() is None:
            return
        video = VIDEO_ROUTE.fullmatch(path)
        if video:
            self._serve_video(video.group(1), video.group(2), head_only=True)
            return
        candidate_video = CANDIDATE_VIDEO_ROUTE.fullmatch(path)
        if candidate_video:
            self._serve_candidate_video(
                candidate_video.group(1), candidate_video.group(2), head_only=True
            )
            return
        candidate_source_video = CANDIDATE_SOURCE_VIDEO_ROUTE.fullmatch(path)
        if candidate_source_video:
            self._serve_candidate_source_video(
                candidate_source_video.group(1), head_only=True
            )
            return
        composition_video = COMPOSITION_VIDEO_ROUTE.fullmatch(path)
        if composition_video:
            self._serve_composition_video(
                composition_video.group(1), composition_video.group(2), head_only=True
            )
            return
        composition_source_video = COMPOSITION_SOURCE_VIDEO_ROUTE.fullmatch(path)
        if composition_source_video:
            self._serve_composition_source_video(
                composition_source_video.group(1), head_only=True
            )
            return
        self._send_error_json(405, "method_not_allowed", "Method not allowed.", {"Allow": "GET"})

    def do_POST(self) -> None:
        if not self._valid_host():
            return
        path = self._request_path()
        if path is None:
            return
        if path == "/api/session":
            self._exchange_session()
            return
        if self._require_mutation_auth() is None:
            return
        if path == CANDIDATE_RUNS_ROUTE:
            self._create_candidate_run()
            return
        finalize = CANDIDATE_FINALIZE_ROUTE.fullmatch(path)
        if finalize:
            self._finalize_candidate_run(finalize.group(1))
            return
        analyze = CANDIDATE_ANALYZE_ROUTE.fullmatch(path)
        if analyze:
            self._start_candidate_analysis(analyze.group(1))
            return
        cancel = CANDIDATE_CANCEL_ROUTE.fullmatch(path)
        if cancel:
            self._cancel_candidate_run(cancel.group(1))
            return
        adopt = CANDIDATE_ADOPT_ROUTE.fullmatch(path)
        if adopt:
            self._adopt_candidate_range(adopt.group(1))
            return
        render = RENDER_CREATE_ROUTE.fullmatch(path)
        if render:
            self._create_render(render.group(1))
            return
        composition_render = COMPOSITION_RENDER_CREATE_ROUTE.fullmatch(path)
        if composition_render:
            self._create_composition_render(composition_render.group(1))
            return
        self._send_error_json(404, "not_found", "Not found.")

    def do_PUT(self) -> None:
        if not self._valid_host():
            return
        path = self._request_path()
        if path is None:
            return
        if self._require_mutation_auth() is None:
            return
        candidate_chunk = CANDIDATE_CHUNK_ROUTE.fullmatch(path)
        if candidate_chunk:
            self._upload_candidate_chunk(
                candidate_chunk.group(1), int(candidate_chunk.group(2))
            )
            return
        captions = CAPTION_SAVE_ROUTE.fullmatch(path)
        if captions:
            self._save_captions(captions.group(1))
            return
        composition_edit = COMPOSITION_EDIT_ROUTE.fullmatch(path)
        if composition_edit:
            self._save_composition_edit(composition_edit.group(1))
            return
        self._send_error_json(404, "not_found", "Not found.")

    def do_OPTIONS(self) -> None:
        if self._valid_host():
            self._send_error_json(405, "method_not_allowed", "Method not allowed.")

    do_DELETE = do_OPTIONS
    do_PATCH = do_OPTIONS

    def _request_path(self) -> str | None:
        parsed = urlsplit(self.path)
        if parsed.query:
            self._send_error_json(404, "not_found", "Not found.")
            return None
        return parsed.path

    def _valid_host(self) -> bool:
        if self.headers.get("Host") != self.server.expected_host:
            self._send_error_json(400, "invalid_host", "Invalid Host header.")
            return False
        return True

    def _session_cookie(self) -> str | None:
        raw = self.headers.get("Cookie", "")
        try:
            cookie = http.cookies.SimpleCookie()
            cookie.load(raw)
        except http.cookies.CookieError:
            return None
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel is not None else None

    def _session(self) -> tuple[str, str] | None:
        session_id = self._session_cookie()
        csrf = self.server.get_csrf(session_id) if session_id else None
        return (session_id, csrf) if session_id and csrf else None

    def _discard_small_request_body(self) -> None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except (TypeError, ValueError):
            self.close_connection = True
            return
        if length < 0 or length > MAX_JSON_BYTES:
            self.close_connection = True
            return
        if length:
            self.rfile.read(length)

    def _require_session(self) -> tuple[str, str] | None:
        session = self._session()
        if session is None:
            self._send_error_json(401, "authentication_required", "Authentication required.")
            return None
        return session

    def _require_mutation_auth(self) -> tuple[str, str] | None:
        session = self._session()
        if session is None:
            self._discard_small_request_body()
            self._send_error_json(401, "authentication_required", "Authentication required.")
            return None
        if self.headers.get("Origin") != self.server.origin:
            self._discard_small_request_body()
            self._send_error_json(403, "invalid_origin", "Invalid request origin.")
            return None
        supplied = self.headers.get("X-CSRF-Token", "")
        if not _bounded_ascii_equal(supplied, session[1]):
            self._discard_small_request_body()
            self._send_error_json(403, "invalid_csrf", "Invalid CSRF token.")
            return None
        return session

    def _exchange_session(self) -> None:
        if self.headers.get("Origin") != self.server.origin:
            self._send_error_json(403, "invalid_origin", "Invalid request origin.")
            return
        try:
            payload = self._read_json()
            if set(payload) != {"launch_token"} or not isinstance(
                payload["launch_token"], str
            ):
                raise RequestError(400, "invalid_request", "Invalid session request.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        if not _bounded_ascii_equal(
            payload["launch_token"], self.server.launch_token
        ):
            self._send_error_json(403, "invalid_launch_token", "Invalid launch token.")
            return
        session_id, csrf = self.server.create_session()
        cookie = (
            f"{SESSION_COOKIE}={session_id}; Path=/; HttpOnly; SameSite=Strict"
        )
        self._send_json(200, {"csrf_token": csrf}, {"Set-Cookie": cookie})

    def _dispatch_get(self, path: str, *, head_only: bool) -> None:
        if path == COMPOSITION_PROJECTS_ROUTE:
            self._composition_json(
                lambda: {
                    "projects": list_composition_projects(
                        self.server.composition_projects_root
                    )
                }
            )
            return
        composition_video = COMPOSITION_VIDEO_ROUTE.fullmatch(path)
        if composition_video:
            self._serve_composition_video(
                composition_video.group(1),
                composition_video.group(2),
                head_only=head_only,
            )
            return
        composition_source_video = COMPOSITION_SOURCE_VIDEO_ROUTE.fullmatch(path)
        if composition_source_video:
            self._serve_composition_source_video(
                composition_source_video.group(1), head_only=head_only
            )
            return
        composition_project = COMPOSITION_PROJECT_ROUTE.fullmatch(path)
        if composition_project:
            self._composition_json(
                lambda: {
                    "composition": project_composition_for_review(
                        safe_composition_project_dir(
                            self.server.composition_projects_root,
                            composition_project.group(1),
                        )
                    )
                }
            )
            return
        if path == CANDIDATE_RUNS_ROUTE:
            self._candidate_json(
                lambda: {
                    "runs": [
                        project_candidate_run(self.server.candidate_root, run["run_id"])
                        for run in list_candidate_runs(self.server.candidate_root)
                    ]
                }
            )
            return
        candidate_video = CANDIDATE_VIDEO_ROUTE.fullmatch(path)
        if candidate_video:
            self._serve_candidate_video(
                candidate_video.group(1),
                candidate_video.group(2),
                head_only=head_only,
            )
            return
        candidate_source_video = CANDIDATE_SOURCE_VIDEO_ROUTE.fullmatch(path)
        if candidate_source_video:
            self._serve_candidate_source_video(
                candidate_source_video.group(1), head_only=head_only
            )
            return
        candidate_run = CANDIDATE_RUN_ROUTE.fullmatch(path)
        if candidate_run:
            self._candidate_json(
                lambda: {
                    "run": project_candidate_run(
                        self.server.candidate_root, candidate_run.group(1)
                    )
                }
            )
            return
        if path == "/api/jobs":
            self._artifact_json(lambda: {"jobs": list(list_workflow_jobs(self.server.jobs_root))})
            return
        operation = OPERATION_ROUTE.fullmatch(path)
        if operation:
            get_status = getattr(self.server.mutation_launcher, "get_status", None)
            status = get_status(operation.group(1)) if callable(get_status) else None
            if status is None:
                self._send_error_json(404, "not_found", "Not found.")
            else:
                self._send_json(200, {"operation": status})
            return
        current = CURRENT_CAPTION_ROUTE.fullmatch(path)
        if current:
            self._artifact_json(
                lambda: {
                    "caption": load_current_caption(self._job_dir(current.group(1)))
                }
            )
            return
        caption = CAPTION_ROUTE.fullmatch(path)
        if caption:
            self._artifact_json(
                lambda: {
                    "caption": load_caption_revision(
                        self._job_dir(caption.group(1)), int(caption.group(2))
                    )
                }
            )
            return
        video = VIDEO_ROUTE.fullmatch(path)
        if video:
            self._serve_video(video.group(1), video.group(2), head_only=head_only)
            return
        render = RENDER_ROUTE.fullmatch(path)
        if render:
            self._artifact_json(
                lambda: {
                    "render": load_render(
                        self._job_dir(render.group(1)), render.group(2)
                    )
                }
            )
            return
        job = JOB_ROUTE.fullmatch(path)
        if job:
            self._artifact_json(
                lambda: {"job": project_job(self._job_dir(job.group(1)))}
            )
            return
        self._send_error_json(404, "not_found", "Not found.")

    def _job_dir(self, job_id: str) -> Path:
        if not SAFE_ID.fullmatch(job_id):
            raise NotFoundError("job not found")
        return safe_job_dir(self.server.jobs_root, job_id)

    def _artifact_json(self, action: Any) -> None:
        try:
            value = action()
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except NotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
        except WorkflowError as exc:
            self._send_error_json(
                int(getattr(exc, "status_code", 400)),
                "workflow_error",
                "Workflow artifact is not available.",
            )
        except (TypeError, ValueError, OSError, json.JSONDecodeError):
            self._send_error_json(500, "invalid_artifact", "Artifact could not be read.")
        else:
            self._send_json(200, value)

    def _candidate_json(self, action: Any, *, success_status: int = 200) -> None:
        try:
            value = action()
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except CandidateNotFoundError:
            self._send_error_json(404, "not_found", "Candidate run was not found.")
        except CandidateConflictError:
            self._send_error_json(
                409, "candidate_conflict", "Candidate run state changed. Reload and try again."
            )
        except CandidateArtifactError:
            self._send_error_json(
                422, "invalid_candidate_request", "Candidate request or artifact is invalid."
            )
        except (TypeError, ValueError, OSError, json.JSONDecodeError):
            self._send_error_json(
                500, "candidate_error", "Candidate state could not be read."
            )
        else:
            self._send_json(success_status, value)

    def _composition_json(self, action: Any, *, success_status: int = 200) -> None:
        try:
            value = action()
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except NotFoundError:
            self._send_error_json(404, "not_found", "Composition was not found.")
        except ConflictError:
            self._send_error_json(409, "composition_conflict", "Composition changed.")
        except ValidationError:
            self._send_error_json(422, "invalid_composition", "Composition is invalid.")
        except (TypeError, ValueError, OSError, json.JSONDecodeError):
            self._send_error_json(
                500, "composition_error", "Composition state could not be read."
            )
        else:
            self._send_json(success_status, value)

    def _create_candidate_run(self) -> None:
        try:
            payload = self._read_json()
            if set(payload) != {"file", "rights"}:
                raise RequestError(400, "invalid_request", "Invalid candidate intake.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return

        def create() -> dict[str, Any]:
            run = create_candidate_run(
                self.server.candidate_root,
                file=payload["file"],
                rights=payload["rights"],
            )
            return {
                "run": project_candidate_run(
                    self.server.candidate_root, run["run_id"]
                )
            }

        self._candidate_json(create, success_status=201)

    def _upload_candidate_chunk(self, run_id: str, index: int) -> None:
        try:
            if self.headers.get("Transfer-Encoding"):
                raise RequestError(400, "invalid_upload", "Chunked transfer is not accepted.")
            raw_length = self.headers.get("Content-Length")
            raw_range = self.headers.get("Content-Range", "")
            supplied_hash = self.headers.get("X-Chunk-SHA256", "").lower()
            if raw_length is None or len(raw_length) > 12 or not raw_length.isdigit():
                raise RequestError(411, "length_required", "Content-Length is required.")
            length = int(raw_length)
            if not 1 <= length <= UPLOAD_CHUNK_BYTES:
                raise RequestError(413, "chunk_too_large", "Upload chunk is too large.")
            match = re.fullmatch(
                r"bytes ([0-9]{1,20})-([0-9]{1,20})/([0-9]{1,20})",
                raw_range,
            )
            if not match or not SHA256.fullmatch(supplied_hash):
                raise RequestError(400, "invalid_upload", "Upload headers are invalid.")
            start, inclusive_end, total = (int(value) for value in match.groups())
            if inclusive_end < start or inclusive_end - start + 1 != length:
                raise RequestError(400, "invalid_upload", "Upload range is invalid.")
            data = self.rfile.read(length)
            if len(data) != length:
                raise RequestError(400, "invalid_upload", "Upload chunk is incomplete.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return

        self._candidate_json(
            lambda: {
                "run": project_candidate_run(
                    self.server.candidate_root,
                    append_upload_chunk(
                        self.server.candidate_root,
                        run_id,
                        index=index,
                        start=start,
                        end=inclusive_end + 1,
                        total=total,
                        data=data,
                        chunk_sha256=supplied_hash,
                    )["run_id"],
                )
            }
        )

    def _finalize_candidate_run(self, run_id: str) -> None:
        try:
            payload = self._read_json()
            if set(payload) != {"size_bytes", "chunk_count"}:
                raise RequestError(400, "invalid_request", "Invalid finalize request.")
            size = payload["size_bytes"]
            count = payload["chunk_count"]
            if (
                isinstance(size, bool)
                or not isinstance(size, int)
                or size < 1
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 1
            ):
                raise RequestError(422, "invalid_upload", "Invalid finalize values.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return

        def finalize() -> dict[str, Any]:
            run = finalize_upload(
                self.server.candidate_root,
                run_id,
                size_bytes=size,
                chunk_count=count,
            )
            return {
                "run": project_candidate_run(
                    self.server.candidate_root, run["run_id"]
                )
            }

        self._candidate_json(finalize)

    def _start_candidate_analysis(self, run_id: str) -> None:
        try:
            payload = self._read_json()
            if payload:
                raise RequestError(400, "invalid_request", "Analysis body must be empty.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        try:
            run = prepare_analysis(self.server.candidate_root, run_id)
            if not self.server.candidate_launcher.launch(run_id):
                update_candidate_status(
                    Path(run["run_dir"]),
                    state="failed",
                    stage="failed",
                    progress=None,
                    error={"code": "launch_failed", "message": "worker launch failed"},
                )
                raise CandidateConflictError("candidate worker could not start")
            value = {
                "run": project_candidate_run(self.server.candidate_root, run_id)
            }
        except CandidateNotFoundError:
            self._send_error_json(404, "not_found", "Candidate run was not found.")
            return
        except CandidateConflictError:
            self._send_error_json(
                409, "candidate_conflict", "Candidate analysis cannot start in this state."
            )
            return
        except CandidateArtifactError:
            self._send_error_json(
                422, "invalid_candidate_request", "Candidate run is invalid."
            )
            return
        except OSError:
            self._send_error_json(500, "candidate_error", "Candidate worker could not start.")
            return
        self._send_json(202, value)

    def _cancel_candidate_run(self, run_id: str) -> None:
        try:
            payload = self._read_json()
            if payload:
                raise RequestError(400, "invalid_request", "Cancel body must be empty.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return

        def cancel() -> dict[str, Any]:
            run = load_candidate_run(self.server.candidate_root, run_id)
            if run["status"]["state"] == "complete":
                raise CandidateConflictError("completed analysis cannot be cancelled")
            run_dir = Path(run["run_dir"])
            request_cancel(run_dir)
            if run["status"]["state"] in {
                "created",
                "uploading",
                "finalized",
                "failed",
                "cancelled",
            }:
                update_candidate_status(
                    run_dir,
                    state="cancelled",
                    stage="cancelled",
                    progress=None,
                )
            return {
                "run": project_candidate_run(self.server.candidate_root, run_id)
            }

        self._candidate_json(cancel, success_status=202)

    def _adopt_candidate_range(self, run_id: str) -> None:
        try:
            payload = self._read_json()
            if set(payload) != {"candidate_id", "start", "end"}:
                raise RequestError(400, "invalid_request", "Invalid candidate range request.")
            candidate_id = payload["candidate_id"]
            start = payload["start"]
            end = payload["end"]
            if not isinstance(candidate_id, str) or not SAFE_ID.fullmatch(candidate_id):
                raise RequestError(422, "invalid_candidate", "Invalid candidate selection.")
            if (
                isinstance(start, bool)
                or isinstance(end, bool)
                or not isinstance(start, (int, float))
                or not isinstance(end, (int, float))
                or not math.isfinite(float(start))
                or not math.isfinite(float(end))
            ):
                raise RequestError(422, "invalid_range", "Invalid candidate range.")
            normalized_start = round(float(start), 3)
            normalized_end = round(float(end), 3)
            source, _ = candidate_source(self.server.candidate_root, run_id)
            candidate_preview(self.server.candidate_root, run_id, candidate_id)
            if (
                normalized_start < 0
                or normalized_end <= normalized_start
                or normalized_end > float(source["duration_seconds"])
                or normalized_end - normalized_start < 15
                or normalized_end - normalized_start > 60
            ):
                raise RequestError(422, "invalid_range", "Candidate range is out of bounds.")
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        except CandidateNotFoundError:
            self._send_error_json(404, "not_found", "Candidate was not found.")
            return
        except CandidateConflictError:
            self._send_error_json(409, "candidate_conflict", "Candidate source changed.")
            return
        except CandidateArtifactError:
            self._send_error_json(422, "invalid_candidate", "Candidate is invalid.")
            return
        outcome = self.server.mutation_launcher.launch_candidate_adopt(
            run_id,
            candidate_id,
            normalized_start,
            normalized_end,
        )
        self._send_launch_outcome(outcome)

    def _save_captions(self, job_id: str) -> None:
        try:
            job_dir = self._job_dir(job_id)
            job = ensure_workflow_job(job_dir)
            max_chars_per_line, max_lines = caption_layout_limits(job)
            payload = self._validate_caption_save(
                self._read_json(),
                load_current_caption(job_dir),
                duration=float(job["duration_seconds"]),
                minimum_duration=caption_duration_floor(job),
                max_chars_per_line=max_chars_per_line,
                max_lines=max_lines,
            )
        except NotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
            return
        except WorkflowError as exc:
            self._send_error_json(
                int(getattr(exc, "status_code", 400)),
                "workflow_error",
                "Workflow artifact is not available.",
            )
            return
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        outcome = self.server.mutation_launcher.launch_save(job_id, payload)
        self._send_launch_outcome(outcome)

    def _create_render(self, job_id: str) -> None:
        try:
            self._job_dir(job_id)
            payload = self._read_json()
            if set(payload) != {"caption_revision"}:
                raise RequestError(400, "invalid_request", "Invalid render request.")
            revision = payload["caption_revision"]
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                raise RequestError(422, "invalid_revision", "Invalid caption revision.")
        except NotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
            return
        except WorkflowError as exc:
            self._send_error_json(
                int(getattr(exc, "status_code", 400)),
                "workflow_error",
                "Workflow artifact is not available.",
            )
            return
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        outcome = self.server.mutation_launcher.launch_render(job_id, revision)
        self._send_launch_outcome(outcome)

    def _save_composition_edit(self, project_id: str) -> None:
        try:
            project_dir = safe_composition_project_dir(
                self.server.composition_projects_root, project_id
            )
            payload = self._read_json()
            if set(payload) != {"base_revision", "plan"}:
                raise RequestError(400, "invalid_request", "Invalid composition edit.")
            revision = payload["base_revision"]
            plan = payload["plan"]
            if (
                isinstance(revision, bool)
                or not isinstance(revision, int)
                or revision < 1
                or not isinstance(plan, dict)
            ):
                raise RequestError(422, "invalid_edit", "Invalid composition edit.")
            if plan.get("project_id") != project_id:
                raise RequestError(422, "invalid_edit", "Project identity does not match.")
            project_composition_for_review(project_dir)
        except NotFoundError:
            self._send_error_json(404, "not_found", "Composition was not found.")
            return
        except (ConflictError, ValidationError):
            self._send_error_json(409, "composition_conflict", "Composition changed.")
            return
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        launch = getattr(self.server.mutation_launcher, "launch_composition_save", None)
        if not callable(launch):
            self._send_error_json(503, "worker_unavailable", "Composition worker is unavailable.")
            return
        outcome = launch(
            self.server.composition_projects_root,
            project_id,
            {"base_revision": revision, "plan": plan},
        )
        self._send_launch_outcome(outcome)

    def _create_composition_render(self, project_id: str) -> None:
        try:
            safe_composition_project_dir(self.server.composition_projects_root, project_id)
            payload = self._read_json()
            if set(payload) != {"edit_revision", "profile"}:
                raise RequestError(400, "invalid_request", "Invalid composition render.")
            revision = payload["edit_revision"]
            profile = payload["profile"]
            if (
                isinstance(revision, bool)
                or not isinstance(revision, int)
                or revision < 1
                or profile not in {"proxy", "final"}
            ):
                raise RequestError(422, "invalid_render", "Invalid composition render.")
        except NotFoundError:
            self._send_error_json(404, "not_found", "Composition was not found.")
            return
        except (ConflictError, ValidationError):
            self._send_error_json(409, "composition_conflict", "Composition changed.")
            return
        except RequestError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
            return
        launch = getattr(self.server.mutation_launcher, "launch_composition_render", None)
        if not callable(launch):
            self._send_error_json(503, "worker_unavailable", "Composition worker is unavailable.")
            return
        outcome = launch(
            self.server.composition_projects_root,
            project_id,
            revision,
            profile,
        )
        self._send_launch_outcome(outcome)

    @staticmethod
    def _validate_caption_save(
        payload: dict[str, Any],
        current: Mapping[str, Any],
        *,
        duration: float,
        minimum_duration: float,
        max_chars_per_line: int,
        max_lines: int,
    ) -> dict[str, Any]:
        if set(payload) != {"base_revision", "cues"}:
            raise RequestError(400, "invalid_request", "Invalid caption save request.")
        base = payload["base_revision"]
        cues = payload["cues"]
        if isinstance(base, bool) or not isinstance(base, int) or base < 1:
            raise RequestError(422, "invalid_revision", "Invalid base revision.")
        if current.get("revision") != base:
            raise RequestError(409, "revision_conflict", "Caption revision changed.")
        current_cues = current.get("cues")
        if (
            not isinstance(cues, list)
            or not isinstance(current_cues, list)
            or not 1 <= len(cues) <= 1000
        ):
            raise RequestError(422, "invalid_cues", "Invalid caption cues.")

        current_ids = [cue.get("id") for cue in current_cues]
        if any(not isinstance(cue_id, str) for cue_id in current_ids):
            raise RequestError(409, "invalid_current_caption", "Current caption is invalid.")
        current_id_set = set(current_ids)
        current_by_id = {
            cue_id: cue for cue_id, cue in zip(current_ids, current_cues, strict=True)
        }
        seen_existing: set[str] = set()
        supplied_existing_ids: list[str] = []
        changed = False
        normalized: list[dict[str, Any]] = []
        previous_end = 0.0
        for index, cue in enumerate(cues):
            if (
                not isinstance(cue, dict)
                or set(cue) != {"id", "start", "end", "text"}
            ):
                raise RequestError(422, "invalid_cue", "Invalid caption cue.")
            cue_id = cue["id"]
            text = cue["text"]
            original: Mapping[str, Any] | None = None
            if cue_id is None:
                changed = True
            else:
                if not isinstance(cue_id, str) or not SAFE_CUE_ID.fullmatch(cue_id):
                    raise RequestError(422, "invalid_cue_id", "Invalid cue ID.")
                if cue_id not in current_id_set:
                    raise RequestError(422, "unknown_cue_id", "Unknown cue ID.")
                if cue_id in seen_existing:
                    raise RequestError(422, "duplicate_cue_id", "Duplicate cue ID.")
                seen_existing.add(cue_id)
                supplied_existing_ids.append(cue_id)
                original = current_by_id[cue_id]

            start = cue["start"]
            end = cue["end"]
            if (
                isinstance(start, bool)
                or isinstance(end, bool)
                or not isinstance(start, (int, float))
                or not isinstance(end, (int, float))
            ):
                raise RequestError(422, "invalid_timing", "Invalid caption timing.")
            raw_start = float(start)
            raw_end = float(end)
            if (
                not math.isfinite(raw_start)
                or not math.isfinite(raw_end)
                or raw_start < 0
                or raw_end > duration
            ):
                raise RequestError(422, "invalid_timing", "Invalid caption timing.")
            start_value = round(raw_start, 3)
            end_value = round(raw_end, 3)
            if (
                start_value < 0
                or end_value <= start_value
                or end_value > duration + 0.001
            ):
                raise RequestError(422, "invalid_timing", "Invalid caption timing.")
            if end_value - start_value < minimum_duration:
                raise RequestError(
                    422,
                    "cue_too_short",
                    "Caption cue duration is too short.",
                )
            if index and start_value < previous_end:
                raise RequestError(422, "overlapping_cues", "Caption cues overlap.")
            if (
                not isinstance(text, str)
                or not text.strip()
                or "\x00" in text
                or len(text) > 500
            ):
                raise RequestError(422, "invalid_text", "Invalid caption text.")
            lines = text.splitlines()
            if len(lines) > max_lines:
                raise RequestError(
                    422,
                    "too_many_lines",
                    "Caption text has too many lines.",
                )
            if any(len(line) > max_chars_per_line for line in lines):
                raise RequestError(
                    422,
                    "line_too_long",
                    "A caption line is too long.",
                )
            if original is not None:
                changed = changed or (
                    start_value != original.get("start")
                    or end_value != original.get("end")
                    or text != original.get("text")
                )
            normalized.append(
                {
                    "id": cue_id,
                    "start": start_value,
                    "end": end_value,
                    "text": text,
                }
            )
            previous_end = end_value

        if supplied_existing_ids != current_ids:
            if set(supplied_existing_ids) != current_id_set:
                raise RequestError(
                    422,
                    "cue_deletion_forbidden",
                    "All existing cue IDs must be preserved.",
                )
            raise RequestError(
                422,
                "cue_reorder_forbidden",
                "Existing cue order must be preserved.",
            )
        if not changed:
            raise RequestError(422, "no_changes", "No caption cue changed.")
        return {"base_revision": base, "cues": normalized}

    def _send_launch_outcome(self, outcome: LaunchOutcome) -> None:
        if outcome.state == "LOCK_ACQUIRED":
            assert outcome.operation_id is not None
            location = f"/api/operations/{outcome.operation_id}"
            self._send_json(
                202,
                {
                    "status": "accepted",
                    "operation_id": outcome.operation_id,
                    "status_url": location,
                },
                {"Retry-After": "1", "Location": location},
            )
        elif outcome.state == "BUSY":
            self._send_error_json(409, "busy", "Another operation is running.")
        else:
            self._send_error_json(502, "worker_start_failed", "Worker failed to start.")

    def _read_json(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise RequestError(400, "invalid_request", "Chunked requests are not supported.")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise RequestError(415, "unsupported_media_type", "JSON is required.")
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError as exc:
            raise RequestError(400, "invalid_request", "Invalid Content-Length.") from exc
        if length < 0 or length > MAX_JSON_BYTES:
            raise RequestError(413, "request_too_large", "Request body is too large.")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise RequestError(400, "invalid_request", "Incomplete request body.")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError(400, "invalid_json", "Invalid JSON.") from exc
        if not isinstance(value, dict):
            raise RequestError(400, "invalid_json", "A JSON object is required.")
        return value

    def _serve_static(self, path: str, *, head_only: bool) -> None:
        filename, content_type = STATIC_FILES[path]
        asset = self.server.webui_root / filename
        try:
            body = asset.read_bytes()
        except OSError:
            self._send_error_json(500, "asset_missing", "UI asset is missing.")
            return
        self._send_bytes(200, body, content_type, head_only=head_only)

    def _serve_video(self, job_id: str, render_id: str, *, head_only: bool) -> None:
        try:
            job_dir = self._job_dir(job_id)
            render = load_render(job_dir, render_id)
            root = job_dir.resolve(strict=True)
            video = confined_job_path(job_dir, "renders", render_id, "short.mp4")
            video.relative_to(root)
            if not video.is_file():
                raise NotFoundError("video not found")
            size = video.stat().st_size
        except (NotFoundError, FileNotFoundError, ValueError):
            self._send_error_json(404, "not_found", "Not found.")
            return
        except WorkflowError:
            self._send_error_json(409, "workflow_conflict", "Workflow state conflict.")
            return
        except OSError:
            self._send_error_json(500, "media_error", "Video could not be read.")
            return

        self._serve_media_path(
            video,
            size=size,
            etag=self._render_etag(render),
            head_only=head_only,
        )

    def _serve_composition_video(
        self, project_id: str, render_id: str, *, head_only: bool
    ) -> None:
        try:
            project_dir = safe_composition_project_dir(
                self.server.composition_projects_root, project_id
            )
            render = load_composition_render(project_dir, render_id)
            video = confined_composition_path(
                project_dir, "renders", render_id, "short.mp4"
            )
            if not video.is_file():
                raise NotFoundError("video not found")
            size = video.stat().st_size
        except NotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
            return
        except (ConflictError, ValidationError):
            self._send_error_json(409, "composition_conflict", "Composition changed.")
            return
        except OSError:
            self._send_error_json(500, "media_error", "Video could not be read.")
            return
        self._serve_media_path(
            video,
            size=size,
            etag=self._render_etag(render),
            head_only=head_only,
        )

    def _serve_composition_source_video(
        self, project_id: str, *, head_only: bool
    ) -> None:
        try:
            project_dir = safe_composition_project_dir(
                self.server.composition_projects_root, project_id
            )
            source, video = composition_source_for_review(project_dir)
            size = int(source["size"])
            digest = str(source["sha256"])
            suffix = video.suffix.lower()
            content_type = "video/webm" if suffix in {".webm", ".mkv"} else "video/mp4"
        except NotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
            return
        except (ConflictError, ValidationError):
            self._send_error_json(409, "composition_conflict", "Composition changed.")
            return
        except OSError:
            self._send_error_json(500, "media_error", "Video could not be read.")
            return
        self._serve_media_path(
            video,
            size=size,
            etag=f'"{digest}"',
            head_only=head_only,
            content_type=content_type,
        )

    def _serve_candidate_video(
        self, run_id: str, candidate_id: str, *, head_only: bool
    ) -> None:
        try:
            candidate, video = candidate_preview(
                self.server.candidate_root, run_id, candidate_id
            )
            preview = candidate.get("preview")
            if not isinstance(preview, Mapping):
                raise CandidateArtifactError("candidate preview is invalid")
            size = video.stat().st_size
            digest = preview.get("sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise CandidateArtifactError("candidate preview identity is invalid")
        except CandidateNotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
            return
        except CandidateConflictError:
            self._send_error_json(409, "candidate_conflict", "Candidate preview changed.")
            return
        except CandidateArtifactError:
            self._send_error_json(422, "invalid_candidate", "Candidate preview is invalid.")
            return
        except OSError:
            self._send_error_json(500, "media_error", "Video could not be read.")
            return
        self._serve_media_path(
            video,
            size=size,
            etag=f'"{digest}"',
            head_only=head_only,
        )

    def _serve_candidate_source_video(self, run_id: str, *, head_only: bool) -> None:
        try:
            source, video = candidate_source(self.server.candidate_root, run_id)
        except CandidateNotFoundError:
            self._send_error_json(404, "not_found", "Not found.")
            return
        except CandidateConflictError:
            self._send_error_json(409, "candidate_conflict", "Candidate source changed.")
            return
        except CandidateArtifactError:
            self._send_error_json(422, "invalid_candidate", "Candidate source is invalid.")
            return
        except OSError:
            self._send_error_json(500, "media_error", "Video could not be read.")
            return
        self._serve_media_path(
            video,
            size=int(source["size_bytes"]),
            etag=f'"{source["sha256"]}"',
            head_only=head_only,
            content_type=str(source["content_type"]),
        )

    def _serve_media_path(
        self,
        video: Path,
        *,
        size: int,
        etag: str | None,
        head_only: bool,
        content_type: str = "video/mp4",
    ) -> None:
        range_header = self.headers.get("Range")
        if range_header and self.headers.get("If-Range") and self.headers.get("If-Range") != etag:
            range_header = None
        try:
            byte_range = self._parse_range(range_header, size) if range_header else None
        except RangeError:
            self._send_bytes(
                416,
                b"",
                content_type,
                head_only=True,
                extra_headers={
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes */{size}",
                },
            )
            return

        if byte_range is None:
            start, end, status = 0, max(0, size - 1), 200
            content_length = size
            extra = {"Accept-Ranges": "bytes"}
        else:
            start, end = byte_range
            status = 206
            content_length = end - start + 1
            extra = {
                "Accept-Ranges": "bytes",
                "Content-Range": f"bytes {start}-{end}/{size}",
            }
        if etag:
            extra["ETag"] = etag
        extra["Content-Disposition"] = "inline"

        self._start_response(status, content_type, content_length, extra)
        if head_only or content_length == 0:
            return
        try:
            with video.open("rb") as handle:
                handle.seek(start)
                remaining = content_length
                while remaining:
                    chunk = handle.read(min(STREAM_CHUNK_BYTES, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            return
        except OSError:
            self.close_connection = True

    @staticmethod
    def _parse_range(header: str, size: int) -> tuple[int, int]:
        if size <= 0 or "," in header:
            raise RangeError
        match = re.fullmatch(r"bytes=([0-9]*)-([0-9]*)", header)
        if not match or (not match.group(1) and not match.group(2)):
            raise RangeError
        first, last = match.groups()
        if len(first) > 20 or len(last) > 20:
            raise RangeError
        try:
            if not first:
                suffix = int(last)
                if suffix <= 0:
                    raise RangeError
                return max(0, size - suffix), size - 1
            start = int(first)
            if start >= size:
                raise RangeError
            end = min(int(last), size - 1) if last else size - 1
        except (ValueError, OverflowError) as exc:
            raise RangeError from exc
        if end < start:
            raise RangeError
        return start, end

    @staticmethod
    def _render_etag(render: Any) -> str | None:
        value: Any = None
        if isinstance(render, Mapping):
            value = render.get("output_hash")
            if value is None and isinstance(render.get("render"), Mapping):
                value = render["render"].get("output_hash")
        if isinstance(value, str) and SHA256.fullmatch(value):
            return f'"{value.lower()}"'
        return None

    def _security_headers(self) -> dict[str, str]:
        return {
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": CSP,
            "Cross-Origin-Resource-Policy": "same-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }

    def _start_response(
        self,
        status: int,
        content_type: str,
        content_length: int,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        headers = self._security_headers()
        if extra_headers:
            headers.update(extra_headers)
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(content_length)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        head_only: bool = False,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._start_response(status, content_type, len(body), extra_headers)
        if not head_only and body:
            self.wfile.write(body)

    def _send_json(
        self,
        status: int,
        value: Any,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        try:
            body = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError):
            self._send_error_json(500, "invalid_response", "Response could not be encoded.")
            return
        self._send_bytes(status, body, "application/json; charset=utf-8", extra_headers=extra_headers)

    def _send_error_json(
        self,
        status: int,
        code: str,
        message: str,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        body = json.dumps(
            {"error": {"code": code, "message": message}},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self._send_bytes(
            status,
            body,
            "application/json; charset=utf-8",
            head_only=self.command == "HEAD",
            extra_headers=extra_headers,
        )


def create_review_server(
    jobs_root: Path,
    *,
    port: int = 0,
    composition_projects_root: Path | None = None,
    launch_token: str | None = None,
    launcher: Any | None = None,
    candidate_launcher: Any | None = None,
    python_executable: str | Path | None = None,
) -> ReviewHTTPServer:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return ReviewHTTPServer(
        jobs_root,
        port,
        composition_projects_root=composition_projects_root,
        launch_token=launch_token,
        launcher=launcher,
        candidate_launcher=candidate_launcher,
        python_executable=python_executable,
    )


def serve_review_ui(
    jobs_root: Path,
    *,
    port: int = 0,
    composition_projects_root: Path | None = None,
    open_browser: bool = False,
    python_executable: str | Path | None = None,
) -> None:
    server = create_review_server(
        jobs_root,
        port=port,
        composition_projects_root=composition_projects_root,
        python_executable=python_executable,
    )
    print(f"REVIEW_UI_URL {server.launch_url}", flush=True)
    if open_browser:
        webbrowser.open(server.launch_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def serve(
    *,
    jobs_root: Path,
    port: int = 0,
    composition_projects_root: Path | None = None,
    open_browser: bool = False,
    python_executable: str | Path | None = None,
) -> int:
    serve_review_ui(
        jobs_root,
        port=port,
        composition_projects_root=composition_projects_root,
        open_browser=open_browser,
        python_executable=python_executable,
    )
    return 0
