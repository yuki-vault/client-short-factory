"use strict";

const elements = {
  connectionBadge: document.querySelector("#connectionBadge"),
  startupPanel: document.querySelector("#startupPanel"),
  startupMessage: document.querySelector("#startupMessage"),
  workspace: document.querySelector("#workspace"),
  candidateModeButton: document.querySelector("#candidateModeButton"),
  compositionModeButton: document.querySelector("#compositionModeButton"),
  candidateWorkspace: document.querySelector("#candidateWorkspace"),
  compositionWorkspace: document.querySelector("#compositionWorkspace"),
  candidateRunIdentity: document.querySelector("#candidateRunIdentity"),
  candidateFileInput: document.querySelector("#candidateFileInput"),
  candidateDropZone: document.querySelector("#candidateDropZone"),
  candidateFilePanel: document.querySelector("#candidateFilePanel"),
  candidateFileName: document.querySelector("#candidateFileName"),
  candidateFileSize: document.querySelector("#candidateFileSize"),
  candidateFileType: document.querySelector("#candidateFileType"),
  candidateFileModified: document.querySelector("#candidateFileModified"),
  candidateRightsCheckbox: document.querySelector("#candidateRightsCheckbox"),
  candidateLocalProcessingCheckbox: document.querySelector("#candidateLocalProcessingCheckbox"),
  candidateLocalProcessingLabel: document.querySelector("#candidateLocalProcessingLabel"),
  candidateProviderDescription: document.querySelector("#candidateProviderDescription"),
  candidateHistoryPanel: document.querySelector("#candidateHistoryPanel"),
  candidateHistorySelect: document.querySelector("#candidateHistorySelect"),
  candidateHistoryOpenButton: document.querySelector("#candidateHistoryOpenButton"),
  candidateFormError: document.querySelector("#candidateFormError"),
  candidateStartButton: document.querySelector("#candidateStartButton"),
  candidateProgressPanel: document.querySelector("#candidateProgressPanel"),
  candidateStateBadge: document.querySelector("#candidateStateBadge"),
  candidateProgressTitle: document.querySelector("#candidateProgressTitle"),
  candidateProgressPercent: document.querySelector("#candidateProgressPercent"),
  candidateProgressBar: document.querySelector("#candidateProgressBar"),
  candidateProgressDetail: document.querySelector("#candidateProgressDetail"),
  candidateRecoveryNote: document.querySelector("#candidateRecoveryNote"),
  candidateCancelButton: document.querySelector("#candidateCancelButton"),
  candidateResumeButton: document.querySelector("#candidateResumeButton"),
  candidateResultsPanel: document.querySelector("#candidateResultsPanel"),
  candidateResultCount: document.querySelector("#candidateResultCount"),
  candidateResultsMessage: document.querySelector("#candidateResultsMessage"),
  candidateResultsGrid: document.querySelector("#candidateResultsGrid"),
  candidateList: document.querySelector("#candidateList"),
  candidatePreviewPanel: document.querySelector("#candidatePreviewPanel"),
  candidatePreviewVideo: document.querySelector("#candidatePreviewVideo"),
  candidatePreviewLabel: document.querySelector("#candidatePreviewLabel"),
  candidateSourceTime: document.querySelector("#candidateSourceTime"),
  candidateRangeEditor: document.querySelector("#candidateRangeEditor"),
  candidateRangeStart: document.querySelector("#candidateRangeStart"),
  candidateRangeEnd: document.querySelector("#candidateRangeEnd"),
  candidateStartFromPlayhead: document.querySelector("#candidateStartFromPlayhead"),
  candidateEndFromPlayhead: document.querySelector("#candidateEndFromPlayhead"),
  candidateSeekStart: document.querySelector("#candidateSeekStart"),
  candidateSeekEnd: document.querySelector("#candidateSeekEnd"),
  candidateLoopCheckbox: document.querySelector("#candidateLoopCheckbox"),
  candidateRangeSummary: document.querySelector("#candidateRangeSummary"),
  candidateRangeError: document.querySelector("#candidateRangeError"),
  candidateAdoptButton: document.querySelector("#candidateAdoptButton"),
  candidateAdoptStatus: document.querySelector("#candidateAdoptStatus"),
  candidateResetButton: document.querySelector("#candidateResetButton"),
  jobSelect: document.querySelector("#jobSelect"),
  reloadButton: document.querySelector("#reloadButton"),
  jobState: document.querySelector("#jobState"),
  videoShell: document.querySelector("#videoShell"),
  videoStage: document.querySelector("#videoStage"),
  previewVideo: document.querySelector("#previewVideo"),
  videoEmpty: document.querySelector("#videoEmpty"),
  livePreviewMask: document.querySelector("#livePreviewMask"),
  liveCaptionOverlay: document.querySelector("#liveCaptionOverlay"),
  liveCaptionText: document.querySelector("#liveCaptionText"),
  livePreviewBadge: document.querySelector("#livePreviewBadge"),
  fullscreenButton: document.querySelector("#fullscreenButton"),
  stepBackButton: document.querySelector("#stepBackButton"),
  stepForwardButton: document.querySelector("#stepForwardButton"),
  previewNotice: document.querySelector("#previewNotice"),
  renderSelect: document.querySelector("#renderSelect"),
  renderButton: document.querySelector("#renderButton"),
  renderIdentity: document.querySelector("#renderIdentity"),
  captionRevision: document.querySelector("#captionRevision"),
  technicalState: document.querySelector("#technicalState"),
  contentState: document.querySelector("#contentState"),
  dirtyBadge: document.querySelector("#dirtyBadge"),
  addCaptionButton: document.querySelector("#addCaptionButton"),
  addCaptionError: document.querySelector("#addCaptionError"),
  captionList: document.querySelector("#captionList"),
  discardButton: document.querySelector("#discardButton"),
  saveButton: document.querySelector("#saveButton"),
  compositionEmpty: document.querySelector("#compositionEmpty"),
  compositionContent: document.querySelector("#compositionContent"),
  compositionProjectSelect: document.querySelector("#compositionProjectSelect"),
  compositionReloadButton: document.querySelector("#compositionReloadButton"),
  compositionRevisionBadge: document.querySelector("#compositionRevisionBadge"),
  compositionDirtyBadge: document.querySelector("#compositionDirtyBadge"),
  compositionValidationMessage: document.querySelector("#compositionValidationMessage"),
  compositionDiscardButton: document.querySelector("#compositionDiscardButton"),
  compositionSaveButton: document.querySelector("#compositionSaveButton"),
  compositionRenderButton: document.querySelector("#compositionRenderButton"),
  compositionDurationBadge: document.querySelector("#compositionDurationBadge"),
  compositionClipList: document.querySelector("#compositionClipList"),
  compositionOutputShell: document.querySelector("#compositionOutputShell"),
  compositionLiveCanvas: document.querySelector("#compositionLiveCanvas"),
  compositionLiveSource: document.querySelector("#compositionLiveSource"),
  compositionLiveControls: document.querySelector("#compositionLiveControls"),
  compositionLivePlayButton: document.querySelector("#compositionLivePlayButton"),
  compositionLiveSeek: document.querySelector("#compositionLiveSeek"),
  compositionLiveTime: document.querySelector("#compositionLiveTime"),
  compositionPreviewVideo: document.querySelector("#compositionPreviewVideo"),
  compositionPreviewEmpty: document.querySelector("#compositionPreviewEmpty"),
  compositionRenderSelect: document.querySelector("#compositionRenderSelect"),
  compositionRenderIdentity: document.querySelector("#compositionRenderIdentity"),
  compositionSourceStage: document.querySelector("#compositionSourceStage"),
  compositionSourceVideo: document.querySelector("#compositionSourceVideo"),
  compositionCropRect: document.querySelector("#compositionCropRect"),
  compositionCropLabel: document.querySelector("#compositionCropLabel"),
  compositionKeepVisibleButton: document.querySelector("#compositionKeepVisibleButton"),
  compositionPinMarker: document.querySelector("#compositionPinMarker"),
  compositionCropStatus: document.querySelector("#compositionCropStatus"),
  compositionInspectorEmpty: document.querySelector("#compositionInspectorEmpty"),
  compositionInspector: document.querySelector("#compositionInspector"),
  compositionClipTiming: document.querySelector("#compositionClipTiming"),
  compositionTrimError: document.querySelector("#compositionTrimError"),
  compositionCaptionCount: document.querySelector("#compositionCaptionCount"),
  compositionCaptionAddButton: document.querySelector("#compositionCaptionAddButton"),
  compositionCaptionList: document.querySelector("#compositionCaptionList"),
  compositionCaptionError: document.querySelector("#compositionCaptionError"),
  compositionCaptionOverviewCount: document.querySelector("#compositionCaptionOverviewCount"),
  compositionCaptionOverviewList: document.querySelector("#compositionCaptionOverviewList"),
  compositionCaptionOverviewEmpty: document.querySelector("#compositionCaptionOverviewEmpty"),
  compositionInspectorNote: document.querySelector("#compositionInspectorNote"),
  statusMessage: document.querySelector("#statusMessage"),
};

const state = {
  csrfToken: "",
  jobs: [],
  job: null,
  caption: null,
  originalCues: [],
  originalById: new Map(),
  timingDrafts: new Map(),
  cueKeys: new WeakMap(),
  nextCueKey: 1,
  validation: { valid: true, errors: new Map() },
  selectedRenderId: "",
  liveFrameRequest: null,
  liveFrameType: "",
  busy: false,
  activeMode: "candidate",
  candidateFile: null,
  candidateRun: null,
  candidateRunId: "",
  candidateSelectedId: "",
  candidateUpload: null,
  candidateUploadLoaded: 0,
  candidatePollTimer: null,
  candidatePolling: false,
  candidateAbortRequested: false,
  candidateBusy: false,
  candidateRuns: [],
  candidateSelected: null,
  candidateRange: null,
  candidateSourceUrl: "",
  compositionProjects: [],
  composition: null,
  compositionPlan: null,
  originalCompositionPlan: null,
  compositionSelectedClipId: "",
  compositionSelectedRenderId: "",
  compositionRegion: "content",
  compositionBusy: false,
  compositionPinArmed: false,
  compositionCropPointer: null,
  compositionPreviewMode: "live",
  compositionLiveSegments: [],
  compositionLiveIndex: 0,
  compositionLiveOutputTime: 0,
  compositionLivePlaying: false,
  compositionLiveFrameRequest: null,
  compositionLiveGeneratedStartedAt: null,
  compositionSection: "cuts",
};

const CANDIDATE_CHUNK_BYTES = 8 * 1024 * 1024;
const CANDIDATE_STORAGE_KEY = "short-factory-current-candidate-run";
const CANDIDATE_ACTIVE_STATES = new Set([
  "queued",
  "accepted",
  "pending",
  "validating",
  "extracting_audio",
  "transcribing",
  "scoring",
  "analyzing",
  "building_previews",
  "generating_previews",
  "running",
  "processing",
]);
const CANDIDATE_RECOVERABLE_STATES = new Set([
  "cancelled",
  "canceled",
  "interrupted",
  "failed",
]);

class ApiError extends Error {
  constructor(status, message, code = "") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function setConnection(label, kind) {
  elements.connectionBadge.textContent = label;
  elements.connectionBadge.className = `badge badge-${kind}`;
}

function showStatus(message, kind = "info") {
  elements.statusMessage.textContent = message;
  elements.statusMessage.className = `status-message status-${kind}`;
  elements.statusMessage.hidden = false;
}

function hideStatus() {
  elements.statusMessage.hidden = true;
}

async function parseResponse(response) {
  const type = response.headers.get("Content-Type") || "";
  const payload = type.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const message = payload?.error?.message || `HTTP ${response.status}`;
    throw new ApiError(response.status, message, payload?.error?.code || "");
  }
  return payload;
}

async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.mutation) {
    headers.set("X-CSRF-Token", state.csrfToken);
  }
  const response = await fetch(path, {
    method: options.method || "GET",
    credentials: "same-origin",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  return parseResponse(response);
}

function candidateRunFrom(payload) {
  if (!payload || typeof payload !== "object") return null;
  const run = payload.run || payload.candidate_run || payload;
  return run && typeof run === "object" ? run : null;
}

function candidateRunIdOf(run = state.candidateRun) {
  const value = run?.run_id ?? run?.id ?? state.candidateRunId;
  return typeof value === "string" && value ? value : "";
}

function candidateStatusOf(run = state.candidateRun) {
  const value = run?.status ?? run?.state ?? "new";
  return typeof value === "string" ? value.toLowerCase() : "new";
}

function candidateItemsOf(run = state.candidateRun) {
  const values =
    run?.candidates ??
    run?.results?.candidates ??
    run?.result?.candidates ??
    run?.candidate_set?.candidates ??
    [];
  return Array.isArray(values) ? values.slice(0, 5) : [];
}

function candidateIdOf(candidate, index = 0) {
  const value = candidate?.candidate_id ?? candidate?.id ?? candidate?.rank ?? index + 1;
  return String(value);
}

function candidateFileMetadata(source) {
  if (!source) return null;
  const name = source.name ?? source.file_name ?? "選択済み動画";
  const size = Number(source.size ?? source.size_bytes ?? 0);
  const type = source.type ?? source.content_type ?? "";
  const modified = Number(source.lastModified ?? source.last_modified_ms ?? 0);
  return {
    name: typeof name === "string" ? name : "選択済み動画",
    size: Number.isFinite(size) && size >= 0 ? size : 0,
    type: typeof type === "string" ? type : "",
    lastModified: Number.isFinite(modified) && modified >= 0 ? modified : 0,
  };
}

function runFileMetadata(run = state.candidateRun) {
  const nested = run?.file ?? run?.source ?? run?.upload?.file;
  if (nested) return candidateFileMetadata(nested);
  if (run?.file_name || run?.size_bytes) {
    return candidateFileMetadata({
      file_name: run.file_name,
      size_bytes: run.size_bytes,
      content_type: run.content_type,
      last_modified_ms: run.last_modified_ms,
    });
  }
  return null;
}

function candidateFilesMatch(left, right) {
  const a = candidateFileMetadata(left);
  const b = candidateFileMetadata(right);
  return Boolean(
    a &&
    b &&
    a.name === b.name &&
    a.size === b.size &&
    (!a.lastModified || !b.lastModified || a.lastModified === b.lastModified)
  );
}

function persistCandidateRun() {
  const runId = candidateRunIdOf();
  if (!runId) {
    localStorage.removeItem(CANDIDATE_STORAGE_KEY);
    return;
  }
  const file = candidateFileMetadata(state.candidateFile) || runFileMetadata();
  localStorage.setItem(
    CANDIDATE_STORAGE_KEY,
    JSON.stringify({ run_id: runId, file })
  );
}

function storedCandidateRun() {
  try {
    const value = JSON.parse(localStorage.getItem(CANDIDATE_STORAGE_KEY) || "null");
    if (!value || typeof value.run_id !== "string" || !value.run_id) return null;
    return value;
  } catch (_error) {
    localStorage.removeItem(CANDIDATE_STORAGE_KEY);
    return null;
  }
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let amount = bytes;
  let unit = -1;
  do {
    amount /= 1024;
    unit += 1;
  } while (amount >= 1024 && unit < units.length - 1);
  return `${amount >= 10 ? amount.toFixed(1) : amount.toFixed(2)} ${units[unit]}`;
}

function setCandidateFileSummary(source) {
  const file = candidateFileMetadata(source);
  elements.candidateFilePanel.hidden = !file;
  if (!file) return;
  elements.candidateFileName.textContent = file.name;
  elements.candidateFileSize.textContent = formatBytes(file.size);
  elements.candidateFileType.textContent = file.type || "形式は処理開始時に確認";
  elements.candidateFileModified.textContent = file.lastModified
    ? new Date(file.lastModified).toLocaleString("ja-JP")
    : "—";
}

function updateCandidateStartState() {
  const ready = Boolean(
    state.candidateFile &&
    elements.candidateRightsCheckbox.checked &&
    elements.candidateLocalProcessingCheckbox.checked &&
    !state.candidateBusy
  );
  elements.candidateStartButton.disabled = !ready;
}

function switchMode(mode, { force = false } = {}) {
  if (!new Set(["candidate", "composition"]).has(mode)) return false;
  if (
    !force &&
    state.activeMode === "composition" &&
    mode !== "composition" &&
    compositionBlockIfDirty()
  ) {
    return false;
  }
  if (state.activeMode === "composition" && mode !== "composition") {
    pauseCompositionLivePreview();
    elements.compositionPreviewVideo.pause();
    elements.compositionSourceVideo.pause();
  }
  state.activeMode = mode;
  const candidateActive = mode === "candidate";
  const compositionActive = mode === "composition";
  elements.candidateWorkspace.hidden = !candidateActive;
  elements.compositionWorkspace.hidden = !compositionActive;
  elements.candidateModeButton.classList.toggle("is-active", candidateActive);
  elements.compositionModeButton.classList.toggle("is-active", compositionActive);
  elements.candidateModeButton.setAttribute("aria-selected", candidateActive ? "true" : "false");
  elements.compositionModeButton.setAttribute(
    "aria-selected",
    compositionActive ? "true" : "false"
  );
  return true;
}

function clearCandidatePreview() {
  elements.candidatePreviewVideo.pause();
  elements.candidatePreviewVideo.removeAttribute("src");
  elements.candidatePreviewVideo.load();
  elements.candidatePreviewPanel.hidden = true;
  elements.candidatePreviewLabel.textContent = "候補を選ぶと元動画の該当位置へ移動します。";
  elements.candidateRangeEditor.hidden = true;
  elements.candidateRangeStart.value = "";
  elements.candidateRangeEnd.value = "";
  elements.candidateRangeError.hidden = true;
  elements.candidateRangeSummary.textContent = "";
  elements.candidateSourceTime.textContent = "—";
  elements.candidateAdoptStatus.textContent = "";
  elements.candidateLoopCheckbox.checked = false;
  state.candidateSelected = null;
  state.candidateRange = null;
  state.candidateSourceUrl = "";
}

function candidateHistoryLabel(run) {
  const file = candidateFileMetadata(run?.file)?.name || "動画";
  const status = candidateStatusOf(run);
  const count = candidateItemsOf(run).length;
  const suffix = status === "complete" ? `${count}件` : status || "保存済み";
  return `${file} · ${suffix}`;
}

async function loadCandidateHistory(preferredRunId = candidateRunIdOf()) {
  const payload = await apiRequest("/api/candidate-runs");
  state.candidateRuns = Array.isArray(payload.runs) ? payload.runs : [];
  elements.candidateHistorySelect.replaceChildren();
  for (const run of state.candidateRuns) {
    const runId = candidateRunIdOf(run);
    if (!runId) continue;
    const option = document.createElement("option");
    option.value = runId;
    option.textContent = candidateHistoryLabel(run);
    elements.candidateHistorySelect.append(option);
  }
  elements.candidateHistoryPanel.hidden = !elements.candidateHistorySelect.options.length;
  if (preferredRunId && state.candidateRuns.some((run) => candidateRunIdOf(run) === preferredRunId)) {
    elements.candidateHistorySelect.value = preferredRunId;
  }
  elements.candidateHistoryOpenButton.disabled = !elements.candidateHistorySelect.value;
}

async function openCandidateHistoryRun(runId = elements.candidateHistorySelect.value) {
  if (!runId || state.candidateBusy) return;
  setCandidateBusy(true);
  try {
    state.candidateRunId = runId;
    const payload = await apiRequest(candidateRunEndpoint());
    updateCandidateRunFromPayload(payload);
    await loadCandidateHistory(runId);
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    setCandidateBusy(false);
  }
}

function resetCandidateClientState({ preserveRun = false } = {}) {
  if (state.candidatePollTimer !== null) {
    clearTimeout(state.candidatePollTimer);
    state.candidatePollTimer = null;
  }
  if (state.candidateUpload) {
    state.candidateUpload.abort();
    state.candidateUpload = null;
  }
  state.candidateFile = null;
  state.candidateSelectedId = "";
  state.candidateAbortRequested = false;
  state.candidateBusy = false;
  if (!preserveRun) {
    state.candidateRun = null;
    state.candidateRunId = "";
    localStorage.removeItem(CANDIDATE_STORAGE_KEY);
  }
  elements.candidateFileInput.value = "";
  elements.candidateRightsCheckbox.checked = false;
  elements.candidateLocalProcessingCheckbox.checked = false;
  elements.candidateFilePanel.hidden = true;
  elements.candidateStartButton.hidden = false;
  elements.candidateProgressPanel.hidden = true;
  elements.candidateResultsPanel.hidden = true;
  elements.candidateFormError.hidden = true;
  elements.candidateDropZone.hidden = false;
  elements.candidateDropZone.querySelector("strong").textContent = "動画をここにドロップ";
  elements.candidateRunIdentity.textContent = "新しい動画";
  clearCandidatePreview();
  updateCandidateStartState();
}

function selectCandidateFile(file) {
  if (!file || typeof file.slice !== "function") return;
  if (file.size <= 0) {
    elements.candidateFormError.textContent = "空のファイルは処理できません。";
    elements.candidateFormError.hidden = false;
    return;
  }
  if (
    state.candidateRun &&
    !candidateFilesMatch(file, runFileMetadata()) &&
    (CANDIDATE_ACTIVE_STATES.has(candidateStatusOf()) || candidateStatusOf() === "uploading")
  ) {
    showStatus("進行中の処理を中止してから別の動画を選んでください。", "error");
    return;
  }
  if (state.candidateRun && !candidateFilesMatch(file, runFileMetadata())) {
    state.candidateRun = null;
    state.candidateRunId = "";
    localStorage.removeItem(CANDIDATE_STORAGE_KEY);
  }
  state.candidateFile = file;
  state.candidateSelectedId = "";
  elements.candidateRightsCheckbox.checked = false;
  elements.candidateLocalProcessingCheckbox.checked = false;
  elements.candidateFormError.hidden = true;
  elements.candidateProgressPanel.hidden = true;
  elements.candidateResultsPanel.hidden = true;
  elements.candidateStartButton.hidden = false;
  elements.candidateDropZone.querySelector("strong").textContent = "別の動画へ変更する場合はここへドロップ";
  setCandidateFileSummary(file);
  clearCandidatePreview();
  updateCandidateStartState();
}

function candidateProgressOf(run = state.candidateRun) {
  const progress = run?.progress && typeof run.progress === "object" ? run.progress : {};
  const completed = Number(
    progress.completed ?? progress.current ?? run?.completed_chunks?.length ?? 0
  );
  const total = Number(progress.total ?? run?.chunk_count ?? 0);
  const suppliedPercent = Number(progress.percent ?? run?.progress_percent);
  const percent = Number.isFinite(suppliedPercent)
    ? Math.min(100, Math.max(0, suppliedPercent))
    : Number.isFinite(completed) && Number.isFinite(total) && total > 0
      ? Math.min(100, Math.max(0, (completed / total) * 100))
      : null;
  return {
    completed: Number.isFinite(completed) ? completed : 0,
    total: Number.isFinite(total) ? total : 0,
    percent,
    message:
      typeof progress.message === "string"
        ? progress.message
        : typeof run?.message === "string"
          ? run.message
          : "",
  };
}

function candidateStagePresentation(status) {
  const selectionProvider = state.candidateRun?.selection?.provider;
  const aiSelectionDetail =
    selectionProvider === "openai-codex"
      ? "Codex CLIが切り抜き候補を評価しています"
      : "LM Studioが切り抜き候補を評価しています";
  const stages = {
    new: ["準備", "動画を選んでください"],
    created: ["準備", "動画をアップロードできます"],
    awaiting_upload: ["待機中", "同じ動画を選び直してください"],
    uploading: ["UPLOAD", "動画をPC内の作業領域へ準備中"],
    uploaded: ["UPLOAD完了", "動画を検証しています"],
    finalized: ["準備完了", "候補抽出を開始します"],
    ready: ["準備完了", "候補抽出を開始します"],
    queued: ["待機中", "候補抽出の開始を待っています"],
    accepted: ["待機中", "候補抽出の開始を待っています"],
    pending: ["待機中", "候補抽出の開始を待っています"],
    validating: ["確認中", "動画の形式と音声を確認しています"],
    extracting_audio: ["音声抽出", "文字起こし用の音声を準備しています"],
    transcribing: ["文字起こし", "Whisperが動画全体を文字起こししています"],
    scoring: ["AI選定", aiSelectionDetail],
    analyzing: ["AI選定", aiSelectionDetail],
    building_previews: ["PREVIEW", "候補の確認用動画を作っています"],
    generating_previews: ["PREVIEW", "候補の確認用動画を作っています"],
    running: ["処理中", "切り抜き候補を探しています"],
    processing: ["処理中", "切り抜き候補を探しています"],
    cancelled: ["中止", "処理を中止しました"],
    canceled: ["中止", "処理を中止しました"],
    interrupted: ["中断", "処理が中断されました"],
    failed: ["エラー", "処理を完了できませんでした"],
    complete: ["完了", "切り抜き候補を確認してください"],
    completed: ["完了", "切り抜き候補を確認してください"],
  };
  return stages[status] || ["処理中", "状態を確認しています"];
}

function setCandidateProgress({ title, detail, percent = null, badge = "処理中", kind = "wait" }) {
  elements.candidateProgressPanel.hidden = false;
  elements.candidateStateBadge.textContent = badge;
  elements.candidateStateBadge.className = `badge badge-${kind}`;
  elements.candidateProgressTitle.textContent = title;
  elements.candidateProgressDetail.textContent = detail || "状態を確認しています。";
  if (Number.isFinite(percent)) {
    const bounded = Math.min(100, Math.max(0, percent));
    elements.candidateProgressBar.value = bounded;
    elements.candidateProgressPercent.textContent = `${Math.round(bounded)}%`;
  } else {
    elements.candidateProgressBar.removeAttribute("value");
    elements.candidateProgressPercent.textContent = "処理中";
  }
}

function candidateValue(candidate, ...keys) {
  for (const key of keys) {
    const value = candidate?.[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "—";
}

function candidateSeconds(candidate, ...keys) {
  for (const key of keys) {
    const value = Number(candidate?.[key]);
    if (Number.isFinite(value) && value >= 0) return value;
  }
  return 0;
}

function appendCandidateDetail(list, label, value) {
  const item = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  item.append(term, description);
  list.append(item);
}

function sameOriginCandidateVideoUrl(runId, candidateId, candidate) {
  const supplied = candidate?.preview_url ?? candidate?.video_url;
  if (typeof supplied === "string" && supplied) {
    try {
      const url = new URL(supplied, location.origin);
      if (url.origin === location.origin) return `${url.pathname}${url.search}`;
    } catch (_error) {
      return "";
    }
  }
  return `/api/candidate-runs/${encodeURIComponent(runId)}/candidates/${encodeURIComponent(candidateId)}/video`;
}

function sameOriginCandidateSourceUrl(run = state.candidateRun) {
  const supplied = run?.source_video_url;
  if (typeof supplied === "string" && supplied) {
    try {
      const url = new URL(supplied, location.origin);
      if (url.origin === location.origin) return `${url.pathname}${url.search}`;
    } catch (_error) {
      return "";
    }
  }
  const runId = candidateRunIdOf(run);
  return runId
    ? `/api/candidate-runs/${encodeURIComponent(runId)}/source/video`
    : "";
}

function candidateSourceDuration() {
  const projected = Number(state.candidateRun?.source_duration_seconds);
  const media = Number(elements.candidatePreviewVideo.duration);
  if (Number.isFinite(projected) && projected > 0) return projected;
  return Number.isFinite(media) && media > 0 ? media : 0;
}

function validateCandidateRange({ normalizeInputs = false } = {}) {
  if (!state.candidateRange || !state.candidateSelected) {
    elements.candidateAdoptButton.disabled = true;
    return false;
  }
  const parsedStart = parseTime(elements.candidateRangeStart.value);
  const parsedEnd = parseTime(elements.candidateRangeEnd.value);
  const duration = candidateSourceDuration();
  let message = "";
  if (parsedStart === null || parsedEnd === null) {
    message = "開始・終了は 01:23:45.67 の形式で入力してください。";
  } else if (parsedStart < 0 || parsedEnd <= parsedStart) {
    message = "終了は開始より後にしてください。";
  } else if (duration > 0 && parsedEnd > duration) {
    message = `終了は元動画 ${formatTime(duration)} 以内にしてください。`;
  } else if (parsedEnd - parsedStart < 15 || parsedEnd - parsedStart > 60) {
    message = "ショート編集へ送る範囲は15〜60秒にしてください。";
  }
  const valid = !message;
  elements.candidateRangeError.textContent = message;
  elements.candidateRangeError.hidden = valid;
  if (valid) {
    state.candidateRange.start = Math.round(parsedStart * 1000) / 1000;
    state.candidateRange.end = Math.round(parsedEnd * 1000) / 1000;
    if (normalizeInputs) {
      elements.candidateRangeStart.value = formatTime(state.candidateRange.start);
      elements.candidateRangeEnd.value = formatTime(state.candidateRange.end);
    }
    elements.candidateRangeSummary.textContent =
      `${formatTime(state.candidateRange.start)}–${formatTime(state.candidateRange.end)} · ` +
      `${(state.candidateRange.end - state.candidateRange.start).toFixed(2)}秒`;
  } else {
    elements.candidateRangeSummary.textContent = "入力中の範囲はまだ採用できません。";
  }
  elements.candidateAdoptButton.disabled = !valid || state.candidateBusy;
  return valid;
}

function seekCandidateSource(seconds) {
  const duration = candidateSourceDuration();
  if (!Number.isFinite(seconds) || duration <= 0) return;
  elements.candidatePreviewVideo.currentTime = Math.min(duration, Math.max(0, seconds));
  elements.candidatePreviewVideo.focus();
}

function setCandidateBoundaryFromPlayhead(field) {
  if (!state.candidateRange) return;
  const current = Number(elements.candidatePreviewVideo.currentTime);
  if (!Number.isFinite(current)) return;
  const input = field === "start" ? elements.candidateRangeStart : elements.candidateRangeEnd;
  input.value = formatTime(Math.round(current * 1000) / 1000);
  validateCandidateRange({ normalizeInputs: true });
}

function selectCandidate(candidate, index, card) {
  const candidateId = candidateIdOf(candidate, index);
  state.candidateSelectedId = candidateId;
  state.candidateSelected = candidate;
  for (const item of elements.candidateList.querySelectorAll(".candidate-card")) {
    const selected = item === card;
    item.classList.toggle("is-selected", selected);
    item.setAttribute("aria-selected", selected ? "true" : "false");
  }
  const runId = candidateRunIdOf();
  const videoUrl = sameOriginCandidateSourceUrl();
  if (!videoUrl) {
    elements.candidatePreviewPanel.hidden = false;
    elements.candidatePreviewLabel.textContent = "このrunの元動画URLは利用できません。";
    return;
  }
  const start = candidateSeconds(candidate, "start", "start_seconds");
  const end = candidateSeconds(candidate, "end", "end_seconds");
  state.candidateRange = { start, end };
  elements.candidateRangeStart.value = formatTime(start);
  elements.candidateRangeEnd.value = formatTime(end);
  if (state.candidateSourceUrl !== videoUrl) {
    state.candidateSourceUrl = videoUrl;
    elements.candidatePreviewVideo.src = videoUrl;
    elements.candidatePreviewVideo.load();
  }
  elements.candidatePreviewPanel.hidden = false;
  elements.candidateRangeEditor.hidden = false;
  validateCandidateRange();
  const rank = Number(candidate?.rank) || index + 1;
  elements.candidatePreviewLabel.textContent =
    `元動画全体です。候補${rank}の開始 ${formatTime(start)} へ移動します。前の実場面もシークして確認できます。`;
  if (elements.candidatePreviewVideo.readyState >= 1) {
    seekCandidateSource(start);
  }
}

function renderCandidateResults(run = state.candidateRun) {
  const candidates = candidateItemsOf(run);
  elements.candidateResultsPanel.hidden = false;
  elements.candidateResultCount.textContent = `${candidates.length}件`;
  elements.candidateList.replaceChildren();
  state.candidateSelectedId = "";
  clearCandidatePreview();

  if (!candidates.length) {
    elements.candidateResultsMessage.textContent =
      "今回は有力な切り抜き候補を見つけられませんでした。エラーではありません。別の動画へ進めます。";
    elements.candidateResultsGrid.hidden = true;
    return;
  }

  elements.candidateResultsMessage.textContent =
    `最大5件のうち${candidates.length}件を提案しました。候補を選ぶと元動画へ移動し、前後をシークして範囲を直せます。`;
  elements.candidateResultsGrid.hidden = false;

  candidates.forEach((candidate, index) => {
    const card = document.createElement("article");
    card.className = "candidate-card";
    card.tabIndex = 0;
    card.setAttribute("role", "option");
    card.setAttribute("aria-selected", "false");

    const header = document.createElement("div");
    header.className = "candidate-card-header";
    const rank = document.createElement("span");
    rank.className = "candidate-card-rank";
    rank.textContent = `候補 ${Number(candidate?.rank) || index + 1}`;
    const time = document.createElement("span");
    time.className = "candidate-card-time";
    const start = candidateSeconds(candidate, "start", "start_seconds");
    const end = candidateSeconds(candidate, "end", "end_seconds");
    const duration = candidateSeconds(candidate, "duration", "duration_seconds") || Math.max(0, end - start);
    time.textContent = `${formatTime(start)}–${formatTime(end)} · ${duration.toFixed(1)}秒`;
    header.append(rank, time);

    const summary = document.createElement("p");
    summary.className = "candidate-card-summary";
    summary.textContent = candidateValue(candidate, "summary", "title");

    const detail = document.createElement("dl");
    detail.className = "candidate-detail";
    appendCandidateDetail(detail, "Hook", candidateValue(candidate, "hook"));
    appendCandidateDetail(detail, "Setup", candidateValue(candidate, "setup"));
    appendCandidateDetail(detail, "Payoff", candidateValue(candidate, "payoff"));
    appendCandidateDetail(detail, "選定理由", candidateValue(candidate, "reason"));
    appendCandidateDetail(detail, "前後文脈", candidateValue(candidate, "context", "context_dependency"));
    appendCandidateDetail(detail, "確認risk", candidateValue(candidate, "risk", "asr_risk"));
    appendCandidateDetail(detail, "推奨mode", candidateValue(candidate, "mode", "recommended_mode"));
    card.append(header, summary, detail);
    card.addEventListener("click", () => selectCandidate(candidate, index, card));
    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectCandidate(candidate, index, card);
    });
    elements.candidateList.append(card);
  });
}

function renderCandidateRun(run = state.candidateRun) {
  if (!run) return;
  state.candidateRun = run;
  state.candidateRunId = candidateRunIdOf(run);
  const usesCodex = run?.selection?.provider === "openai-codex";
  elements.candidateProviderDescription.textContent = usesCodex
    ? "文字起こしはPC内で完了済みです。このrunは個別の明示許可に基づき、時刻付きtranscriptだけをCodex CLIで評価します。動画・音声・frameは外部へ送りません。"
    : "動画はPC内で文字起こしし、LM Studioが最大5件を提案します。有力な箇所がなければ0件で完了します。";
  elements.candidateLocalProcessingLabel.textContent = usesCodex
    ? "このrunには記録済みのCodex CLI利用許可があります"
    : "PC内のWhisperとLM Studioで動画・音声・文字起こしを処理してよいです";
  persistCandidateRun();
  const runId = candidateRunIdOf(run);
  const status = candidateStatusOf(run);
  elements.candidateRunIdentity.textContent = runId ? `run ${runId}` : "candidate run";
  const file = state.candidateFile || runFileMetadata(run);
  if (file) setCandidateFileSummary(file);

  const completed = status === "complete" || status === "completed";
  const recoverable = CANDIDATE_RECOVERABLE_STATES.has(status);
  const active = CANDIDATE_ACTIVE_STATES.has(status);
  const uploadState = ["created", "awaiting_upload", "uploading"].includes(status);
  elements.candidateResultsPanel.hidden = !completed;
  elements.candidateProgressPanel.hidden = !(active || recoverable || uploadState);
  elements.candidateCancelButton.hidden = !(active || status === "uploading");
  elements.candidateResumeButton.hidden = !recoverable;
  elements.candidateRecoveryNote.hidden = !recoverable;
  elements.candidateDropZone.hidden = active || completed || status === "uploading";
  elements.candidateStartButton.hidden = active || completed || recoverable || uploadState;

  if (completed) {
    elements.candidateProgressPanel.hidden = true;
    renderCandidateResults(run);
    void loadCandidateHistory(runId).catch(() => {});
    return;
  }

  if (recoverable) {
    const [, title] = candidateStagePresentation(status);
    const message =
      typeof run?.error?.message === "string"
        ? run.error.message
        : typeof run?.message === "string"
          ? run.message
          : "完了済みの処理は保持されています。";
    setCandidateProgress({
      title,
      detail: message,
      badge: status === "failed" ? "エラー" : "中断",
      kind: status === "failed" ? "error" : "wait",
    });
    const sourceReady = Boolean(run?.source_ready ?? run?.upload?.complete ?? run?.uploaded);
    elements.candidateRecoveryNote.textContent = sourceReady
      ? "元動画と完了済みchunkは保持されています。「続きから再開」で再利用します。"
      : "upload途中のため、同じ動画をもう一度選ぶ必要があります。完了済みchunkがあれば再利用します。";
    elements.candidateResumeButton.textContent = sourceReady
      ? "続きから再開"
      : "同じ動画を選び直す";
    return;
  }

  if (active || uploadState) {
    const [badge, title] = candidateStagePresentation(status);
    const progress = candidateProgressOf(run);
    const count = progress.total > 0
      ? `${progress.completed}/${progress.total}`
      : "";
    setCandidateProgress({
      title,
      detail: progress.message || (count ? `${count} を完了` : "安全に処理を続けています。"),
      percent: progress.percent,
      badge,
    });
  }
}

function setCandidateBusy(value) {
  state.candidateBusy = value;
  elements.candidateFileInput.disabled = value;
  elements.candidateDropZone.setAttribute("aria-disabled", value ? "true" : "false");
  elements.candidateRightsCheckbox.disabled = value;
  elements.candidateLocalProcessingCheckbox.disabled = value;
  elements.candidateCancelButton.disabled = false;
  elements.candidateResumeButton.disabled = value;
  elements.candidateResetButton.disabled = value;
  elements.candidateHistorySelect.disabled = value;
  elements.candidateHistoryOpenButton.disabled = value || !elements.candidateHistorySelect.value;
  for (const control of elements.candidateRangeEditor.querySelectorAll("input, button")) {
    control.disabled = value;
  }
  for (const control of document.querySelectorAll("[data-candidate-seek]")) {
    control.disabled = value;
  }
  if (!value) validateCandidateRange();
  updateCandidateStartState();
}

function candidateRunEndpoint(suffix = "") {
  const runId = candidateRunIdOf();
  if (!runId) throw new Error("candidate run IDがありません。");
  return `/api/candidate-runs/${encodeURIComponent(runId)}${suffix}`;
}

function updateCandidateRunFromPayload(payload) {
  const run = candidateRunFrom(payload);
  if (!run) return null;
  const explicitId = run?.run_id ?? run?.id;
  const runId = typeof explicitId === "string" && explicitId
    ? explicitId
    : state.candidateRunId;
  if (!runId) throw new Error("candidate run IDが応答にありません。");
  state.candidateRun = explicitId
    ? run
    : { ...(state.candidateRun || {}), ...run, run_id: runId };
  state.candidateRunId = runId;
  renderCandidateRun(state.candidateRun);
  return state.candidateRun;
}

async function createCandidateRun() {
  const file = candidateFileMetadata(state.candidateFile);
  const payload = await apiRequest("/api/candidate-runs", {
    method: "POST",
    mutation: true,
    body: {
      file: {
        name: file.name,
        size_bytes: file.size,
        content_type: file.type,
        last_modified_ms: file.lastModified,
      },
      rights: {
        edit_analysis_confirmed: true,
        local_processing_confirmed: true,
      },
    },
  });
  const run = updateCandidateRunFromPayload(payload);
  if (!run) throw new Error("candidate runを作成できませんでした。");
  return run;
}

async function sha256Hex(blob) {
  if (!globalThis.crypto?.subtle) {
    throw new Error("このブラウザでは安全なchunk検証を利用できません。");
  }
  const bytes = await blob.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join("");
}

function uploadCandidateChunk({ runId, index, chunk, start, end, total, hash }) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    state.candidateUpload = request;
    request.open(
      "PUT",
      `/api/candidate-runs/${encodeURIComponent(runId)}/chunks/${index}`
    );
    request.withCredentials = true;
    request.setRequestHeader("Content-Type", "application/octet-stream");
    request.setRequestHeader("X-CSRF-Token", state.csrfToken);
    request.setRequestHeader("X-Chunk-SHA256", hash);
    request.setRequestHeader("Content-Range", `bytes ${start}-${end - 1}/${total}`);
    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      const loaded = start + event.loaded;
      state.candidateUploadLoaded = loaded;
      const percent = total > 0 ? (loaded / total) * 100 : 0;
      setCandidateProgress({
        title: "動画をPC内の作業領域へ準備中",
        detail: `${formatBytes(loaded)} / ${formatBytes(total)} · chunk ${index + 1}/${Math.ceil(total / CANDIDATE_CHUNK_BYTES)}`,
        percent,
        badge: "UPLOAD",
      });
    });
    request.addEventListener("load", () => {
      state.candidateUpload = null;
      let payload = null;
      try {
        payload = request.responseText ? JSON.parse(request.responseText) : null;
      } catch (_error) {
        payload = null;
      }
      if (request.status >= 200 && request.status < 300) {
        resolve(payload);
        return;
      }
      const message = payload?.error?.message || `chunk upload HTTP ${request.status}`;
      reject(new ApiError(request.status, message, payload?.error?.code || ""));
    });
    request.addEventListener("error", () => {
      state.candidateUpload = null;
      reject(new Error("chunk upload中に接続が切れました。同じ動画から再開できます。"));
    });
    request.addEventListener("abort", () => {
      state.candidateUpload = null;
      const error = new Error("uploadを中止しました。");
      error.name = "AbortError";
      reject(error);
    });
    request.send(chunk);
  });
}

async function uploadCandidateFile() {
  const file = state.candidateFile;
  const runId = candidateRunIdOf();
  if (!file || !runId) throw new Error("uploadする動画またはrun IDがありません。");
  const chunkCount = Math.ceil(file.size / CANDIDATE_CHUNK_BYTES);
  elements.candidateProgressPanel.hidden = false;
  elements.candidateCancelButton.hidden = false;
  elements.candidateStartButton.hidden = true;
  // Re-send already committed chunks on resume. The server treats matching
  // chunks idempotently and rejects a same-name/size file with different bytes,
  // preventing an old prefix from being combined with a newly selected file.
  let index = 0;
  for (; index < chunkCount; index += 1) {
    if (state.candidateAbortRequested) {
      const error = new Error("uploadを中止しました。");
      error.name = "AbortError";
      throw error;
    }
    const start = index * CANDIDATE_CHUNK_BYTES;
    const end = Math.min(file.size, start + CANDIDATE_CHUNK_BYTES);
    const chunk = file.slice(start, end);
    setCandidateProgress({
      title: "動画chunkを検証しています",
      detail: `chunk ${index + 1}/${chunkCount} のSHA-256を計算中`,
      percent: file.size > 0 ? (start / file.size) * 100 : 0,
      badge: "UPLOAD",
    });
    const hash = await sha256Hex(chunk);
    if (state.candidateAbortRequested) {
      const error = new Error("uploadを中止しました。");
      error.name = "AbortError";
      throw error;
    }
    const payload = await uploadCandidateChunk({
      runId,
      index,
      chunk,
      start,
      end,
      total: file.size,
      hash,
    });
    updateCandidateRunFromPayload(payload);
  }
  const payload = await apiRequest(candidateRunEndpoint("/finalize"), {
    method: "POST",
    mutation: true,
    body: {
      size_bytes: file.size,
      chunk_count: chunkCount,
    },
  });
  updateCandidateRunFromPayload(payload);
}

function scheduleCandidatePoll(delay = 1000) {
  if (state.candidatePollTimer !== null) clearTimeout(state.candidatePollTimer);
  state.candidatePollTimer = setTimeout(pollCandidateRun, delay);
}

async function pollCandidateRun() {
  if (state.candidatePolling || !candidateRunIdOf()) return;
  state.candidatePolling = true;
  try {
    const payload = await apiRequest(candidateRunEndpoint());
    const run = updateCandidateRunFromPayload(payload);
    const status = candidateStatusOf(run);
    if (CANDIDATE_ACTIVE_STATES.has(status) || status === "uploading") {
      scheduleCandidatePoll();
    }
  } catch (error) {
    elements.candidateProgressPanel.hidden = false;
    elements.candidateRecoveryNote.textContent =
      `状態確認に失敗しました。runは失われていません。再読込または再開を試してください。${error.message}`;
    elements.candidateRecoveryNote.hidden = false;
    elements.candidateResumeButton.hidden = false;
    elements.candidateCancelButton.hidden = true;
  } finally {
    state.candidatePolling = false;
  }
}

async function startCandidateAnalysis() {
  const payload = await apiRequest(candidateRunEndpoint("/analyze"), {
    method: "POST",
    mutation: true,
    body: {},
  });
  updateCandidateRunFromPayload(payload);
  scheduleCandidatePoll(250);
}

async function startCandidateSearch() {
  if (
    !state.candidateFile ||
    !elements.candidateRightsCheckbox.checked ||
    !elements.candidateLocalProcessingCheckbox.checked ||
    state.candidateBusy
  ) {
    return;
  }
  state.candidateAbortRequested = false;
  elements.candidateFormError.hidden = true;
  elements.candidateResultsPanel.hidden = true;
  setCandidateBusy(true);
  try {
    if (!state.candidateRun || !candidateFilesMatch(state.candidateFile, runFileMetadata())) {
      await createCandidateRun();
    }
    const status = candidateStatusOf();
    if (!["uploaded", "finalized", "ready"].includes(status)) {
      await uploadCandidateFile();
    }
    if (!state.candidateAbortRequested) await startCandidateAnalysis();
  } catch (error) {
    if (error.name !== "AbortError") {
      elements.candidateFormError.textContent = error.message;
      elements.candidateFormError.hidden = false;
      showStatus(error.message, "error");
      if (candidateRunIdOf()) scheduleCandidatePoll(500);
    }
  } finally {
    setCandidateBusy(false);
  }
}

async function cancelCandidateRun() {
  if (!candidateRunIdOf()) return;
  state.candidateAbortRequested = true;
  if (state.candidateUpload) state.candidateUpload.abort();
  elements.candidateCancelButton.disabled = true;
  try {
    const payload = await apiRequest(candidateRunEndpoint("/cancel"), {
      method: "POST",
      mutation: true,
      body: {},
    });
    updateCandidateRunFromPayload(payload);
  } catch (error) {
    showStatus(`中止状態の確認に失敗しました。${error.message}`, "error");
    scheduleCandidatePoll(500);
  } finally {
    elements.candidateCancelButton.disabled = false;
  }
}

async function resumeCandidateRun() {
  if (!candidateRunIdOf()) return;
  const run = state.candidateRun;
  const sourceReady = Boolean(
    run?.source_ready ?? run?.upload?.complete ?? run?.uploaded ??
    ["uploaded", "finalized", "ready"].includes(candidateStatusOf(run))
  );
  if (!sourceReady && !state.candidateFile) {
    elements.candidateFileInput.click();
    return;
  }
  state.candidateAbortRequested = false;
  setCandidateBusy(true);
  try {
    if (!sourceReady) {
      await uploadCandidateFile();
      await startCandidateAnalysis();
      return;
    }
    const payload = await apiRequest(candidateRunEndpoint("/resume"), {
      method: "POST",
      mutation: true,
      body: {},
    });
    updateCandidateRunFromPayload(payload);
    scheduleCandidatePoll(250);
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    setCandidateBusy(false);
  }
}

async function restoreCandidateRun() {
  const stored = storedCandidateRun();
  if (!stored) {
    const latestCompleted = state.candidateRuns.find(
      (run) => candidateStatusOf(run) === "complete"
    );
    if (latestCompleted) {
      await openCandidateHistoryRun(candidateRunIdOf(latestCompleted));
    }
    return;
  }
  state.candidateRunId = stored.run_id;
  try {
    const payload = await apiRequest(candidateRunEndpoint());
    const run = updateCandidateRunFromPayload(payload);
    const status = candidateStatusOf(run);
    if (CANDIDATE_ACTIVE_STATES.has(status) || status === "uploading") {
      scheduleCandidatePoll();
    }
  } catch (error) {
    if (error.status === 404) {
      resetCandidateClientState();
      return;
    }
    state.candidateRunId = stored.run_id;
    setCandidateFileSummary(stored.file);
    elements.candidateProgressPanel.hidden = false;
    elements.candidateRecoveryNote.textContent =
      "前回のrunを確認できませんでした。接続後に再読込してください。";
    elements.candidateRecoveryNote.hidden = false;
    elements.candidateResumeButton.hidden = false;
  }
}

async function establishSession() {
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  const launchToken = fragment.get("token");
  const requestedCandidateRun = fragment.get("run");
  let payload;
  if (launchToken) {
    payload = await apiRequest("/api/session", {
      method: "POST",
      body: { launch_token: launchToken },
    });
    history.replaceState(null, "", `${location.pathname}${location.search}`);
  } else {
    payload = await apiRequest("/api/session");
  }
  state.csrfToken = payload.csrf_token;
  if (!state.csrfToken) {
    throw new Error("CSRF token was not issued.");
  }
  if (
    typeof requestedCandidateRun === "string" &&
    /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(requestedCandidateRun)
  ) {
    state.candidateRunId = requestedCandidateRun;
    localStorage.setItem(
      CANDIDATE_STORAGE_KEY,
      JSON.stringify({ run_id: requestedCandidateRun, file: null })
    );
  }
}

function jobIdOf(job) {
  if (typeof job === "string") return job;
  return job?.job_id || "";
}

async function loadJobs(preferredJobId = "") {
  const payload = await apiRequest("/api/jobs");
  state.jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
  elements.jobSelect.replaceChildren();
  for (const job of state.jobs) {
    const jobId = jobIdOf(job);
    if (!jobId) continue;
    const option = document.createElement("option");
    option.value = jobId;
    option.textContent = jobId;
    elements.jobSelect.append(option);
  }
  if (!elements.jobSelect.options.length) {
    state.job = null;
    state.caption = null;
    elements.editorContent.hidden = true;
    elements.editorEmpty.hidden = false;
    elements.editorModeButton.disabled = false;
    return;
  }
  elements.editorContent.hidden = false;
  elements.editorEmpty.hidden = true;
  elements.editorModeButton.disabled = false;
  const selected = state.jobs.some((job) => jobIdOf(job) === preferredJobId)
    ? preferredJobId
    : elements.jobSelect.value;
  elements.jobSelect.value = selected;
  await loadJob(selected);
}

async function loadJob(jobId, preferredRenderId = "") {
  setBusy(true);
  hideStatus();
  try {
    const encodedJob = encodeURIComponent(jobId);
    const [jobPayload, captionPayload] = await Promise.all([
      apiRequest(`/api/jobs/${encodedJob}`),
      apiRequest(`/api/jobs/${encodedJob}/captions/current`),
    ]);
    state.job = jobPayload.job;
    state.caption = captionPayload.caption;
    if (!state.job || !state.caption || !Array.isArray(state.caption.cues)) {
      throw new Error("job artifactの形式が不正です。");
    }
    state.originalCues = snapshotCues(state.caption.cues);
    state.originalById = new Map(
      state.originalCues.map((cue) => [cue.id, cue])
    );
    initializeTimingDrafts();
    elements.addCaptionError.hidden = true;
    renderJobState(preferredRenderId);
    renderCaptionRows();
    updateDirtyState();
  } finally {
    setBusy(false);
  }
}

function renderJobState(preferredRenderId) {
  const renders = Array.isArray(state.job.renders) ? state.job.renders : [];
  elements.captionRevision.textContent = `v${state.caption.revision}`;
  elements.technicalState.textContent = state.job.technical_state || "pending";
  elements.contentState.textContent = state.job.content_state || "pending";
  elements.jobState.textContent = `${state.job.job_id} · ${formatDuration(state.job.duration_seconds)}`;

  elements.renderSelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "renderを選択";
  elements.renderSelect.append(placeholder);
  for (const render of renders) {
    if (!render?.render_id) continue;
    const option = document.createElement("option");
    option.value = render.render_id;
    const stale = render.caption_revision !== state.caption.revision ? " · 前版" : "";
    option.textContent = `${render.render_id} · 字幕v${render.caption_revision}${stale}`;
    elements.renderSelect.append(option);
  }

  const preferred = renders.find((item) => item.render_id === preferredRenderId);
  const currentMatches = renders.filter(
    (item) => item.caption_revision === state.caption.revision
  );
  const selected = preferred || (currentMatches.length === 1 ? currentMatches[0] : null);
  state.selectedRenderId = selected?.render_id || "";
  elements.renderSelect.value = state.selectedRenderId;
  if (!preferred && currentMatches.length > 1) {
    placeholder.textContent = `renderを選択（字幕v${state.caption.revision}に複数あり）`;
  }
  updateVideo(selected);
}

function updateVideo(render) {
  if (!render?.render_id || !state.job?.job_id) {
    stopLiveCaptionFrames();
    elements.previewVideo.removeAttribute("src");
    elements.previewVideo.load();
    elements.previewVideo.hidden = true;
    elements.fullscreenButton.hidden = true;
    elements.stepBackButton.disabled = true;
    elements.stepForwardButton.disabled = true;
    elements.videoEmpty.hidden = false;
    elements.renderIdentity.textContent = "render未選択";
    elements.technicalState.textContent = "pending";
    elements.contentState.textContent = "pending";
    paintLiveCaption();
    return;
  }
  const jobId = encodeURIComponent(state.job.job_id);
  const renderId = encodeURIComponent(render.render_id);
  elements.previewVideo.src = `/api/jobs/${jobId}/renders/${renderId}/video`;
  elements.previewVideo.hidden = false;
  elements.fullscreenButton.hidden = false;
  elements.stepBackButton.disabled = state.busy;
  elements.stepForwardButton.disabled = state.busy;
  elements.videoEmpty.hidden = true;
  const hash = typeof render.output_hash === "string" ? render.output_hash.slice(-10) : "hash不明";
  const stale = render.caption_revision !== state.caption.revision;
  elements.renderIdentity.textContent = stale
    ? `字幕v${render.caption_revision} · ${hash} · 履歴・納品不可`
    : `字幕v${render.caption_revision} · ${hash}`;
  elements.technicalState.textContent = render.technical_checks_passed
    ? stale
      ? "passed（履歴）"
      : "passed"
    : "failed";
  elements.contentState.textContent = stale ? "履歴・未確認" : "pending";
  paintLiveCaption();
}

function videoCanShowLiveDraft() {
  return (
    !elements.previewVideo.hidden &&
    Boolean(elements.previewVideo.getAttribute("src")) &&
    elements.previewVideo.readyState >= HTMLMediaElement.HAVE_METADATA
  );
}

function activeCuesAt(mediaTime) {
  if (!state.caption || !Number.isFinite(mediaTime)) return [];
  return state.caption.cues.filter((cue) => {
    const start = timingValue(cue, "start");
    const end = timingValue(cue, "end");
    return (
      Number.isFinite(start) &&
      Number.isFinite(end) &&
      start <= mediaTime &&
      mediaTime < end
    );
  });
}

function paintLiveCaption(mediaTime = Number(elements.previewVideo.currentTime)) {
  const dirty = isDirty();
  const enabled = dirty && videoCanShowLiveDraft();
  elements.livePreviewMask.hidden = !enabled;
  elements.livePreviewBadge.hidden = !enabled;
  elements.liveCaptionOverlay.hidden = true;
  elements.liveCaptionText.textContent = "";
  if (!enabled) return;

  const active = activeCuesAt(mediaTime);
  if (active.length > 1) {
    elements.livePreviewBadge.textContent = "LIVE DRAFT · 時間重複";
    return;
  }
  elements.livePreviewBadge.textContent = state.validation.valid
    ? "LIVE DRAFT · 未書き出し"
    : "LIVE DRAFT · 入力エラー";
  if (active.length !== 1 || typeof active[0].text !== "string" || !active[0].text) {
    return;
  }
  elements.liveCaptionText.textContent = active[0].text;
  elements.liveCaptionOverlay.hidden = false;
}

function stopLiveCaptionFrames() {
  if (state.liveFrameRequest === null) return;
  if (
    state.liveFrameType === "video" &&
    typeof elements.previewVideo.cancelVideoFrameCallback === "function"
  ) {
    elements.previewVideo.cancelVideoFrameCallback(state.liveFrameRequest);
  } else {
    cancelAnimationFrame(state.liveFrameRequest);
  }
  state.liveFrameRequest = null;
  state.liveFrameType = "";
}

function scheduleLiveCaptionFrame() {
  if (
    state.liveFrameRequest !== null ||
    elements.previewVideo.paused ||
    elements.previewVideo.ended ||
    !isDirty()
  ) {
    return;
  }
  if (typeof elements.previewVideo.requestVideoFrameCallback === "function") {
    state.liveFrameType = "video";
    state.liveFrameRequest = elements.previewVideo.requestVideoFrameCallback(
      (_now, metadata) => {
        state.liveFrameRequest = null;
        state.liveFrameType = "";
        paintLiveCaption(Number(metadata.mediaTime));
        scheduleLiveCaptionFrame();
      }
    );
  } else {
    state.liveFrameType = "animation";
    state.liveFrameRequest = requestAnimationFrame(() => {
      state.liveFrameRequest = null;
      state.liveFrameType = "";
      paintLiveCaption();
      scheduleLiveCaptionFrame();
    });
  }
}

function refreshLiveCaption() {
  const dirty = isDirty();
  elements.previewNotice.hidden = !dirty;
  if (dirty) {
    elements.previewNotice.textContent = videoCanShowLiveDraft()
      ? "未保存の字幕を動画へ即時表示しています。最終確認は保存後のrenderで行います。"
      : "ライブ確認するには、書き出し済みrenderを選択してください。";
  }
  paintLiveCaption();
  if (dirty && !elements.previewVideo.paused) {
    scheduleLiveCaptionFrame();
  } else {
    stopLiveCaptionFrames();
  }
}

function snapshotCues(cues) {
  return cues.map(({ id, start, end, text }) => ({ id, start, end, text }));
}

function cueKey(cue) {
  if (cue.id) return cue.id;
  let key = state.cueKeys.get(cue);
  if (!key) {
    key = `new-${state.nextCueKey++}`;
    state.cueKeys.set(cue, key);
  }
  return key;
}

function initializeTimingDrafts() {
  state.timingDrafts = new Map();
  for (const cue of state.caption.cues) {
    const startRaw = formatTime(cue.start);
    const endRaw = formatTime(cue.end);
    state.timingDrafts.set(cueKey(cue), {
      startRaw,
      endRaw,
      initialStartRaw: startRaw,
      initialEndRaw: endRaw,
      initialStart: cue.start,
      initialEnd: cue.end,
      startTouched: false,
      endTouched: false,
    });
  }
}

function timingDraft(cue) {
  return state.timingDrafts.get(cueKey(cue));
}

function parseTime(value) {
  const match = /^(\d{1,4}):([0-5]\d)\.(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const seconds = Number(match[1]) * 60 + Number(match[2]) + Number(match[3]) / 100;
  return Number.isFinite(seconds) ? seconds : null;
}

function roundCentisecond(value) {
  return Math.round(value * 100) / 100;
}

function floorCentisecond(value) {
  return Math.floor((value + Number.EPSILON) * 100) / 100;
}

function minimumCueSeconds() {
  const projected = Number(state.job?.caption_minimum_seconds ?? 0.65);
  return Math.max(0.01, Number.isFinite(projected) ? projected : 0.65);
}

function maximumCharsPerLine() {
  const projected = Number(state.job?.caption_max_chars_per_line ?? 15);
  return Number.isInteger(projected) && projected > 0 ? projected : 15;
}

function maximumCaptionLines() {
  const projected = Number(state.job?.caption_max_lines ?? 2);
  return Number.isInteger(projected) && projected > 0 ? projected : 2;
}

function timingValue(cue, field) {
  const draft = timingDraft(cue);
  if (!draft) return null;
  if (!draft[`${field}Touched`]) return Number(cue[field]);
  return parseTime(draft[`${field}Raw`]);
}

function cueIsDirty(cue) {
  if (!cue.id) return true;
  const original = state.originalById.get(cue.id);
  const draft = timingDraft(cue);
  if (!original || !draft) return true;
  return (
    cue.text !== original.text ||
    cue.start !== original.start ||
    cue.end !== original.end ||
    draft.startRaw !== draft.initialStartRaw ||
    draft.endRaw !== draft.initialEndRaw
  );
}

function isDirty() {
  if (!state.caption) return false;
  if (JSON.stringify(snapshotCues(state.caption.cues)) !== JSON.stringify(state.originalCues)) {
    return true;
  }
  return state.caption.cues.some((cue) => {
    const draft = timingDraft(cue);
    return Boolean(
      draft &&
      (draft.startRaw !== draft.initialStartRaw || draft.endRaw !== draft.initialEndRaw)
    );
  });
}

function validateCaptionDraft() {
  const errors = new Map();
  const values = [];
  const duration = Number(state.job?.duration_seconds);
  const minimum = minimumCueSeconds();
  const maximumCharacters = maximumCharsPerLine();
  const maximumLines = maximumCaptionLines();
  const addError = (key, message) => {
    const current = errors.get(key) || [];
    if (!current.includes(message)) current.push(message);
    errors.set(key, current);
  };

  state.caption.cues.forEach((cue) => {
    const key = cueKey(cue);
    const start = timingValue(cue, "start");
    const end = timingValue(cue, "end");
    values.push({ key, start, end });
    if (typeof cue.text !== "string" || !cue.text.trim()) {
      addError(key, "字幕本文を入力してください。");
    } else {
      if (cue.text.includes("\0")) {
        addError(key, "字幕本文に使用できない文字が含まれています。");
      }
      if (cue.text.length > 500) {
        addError(key, "字幕本文は500文字以内にしてください。");
      }
      const lines = cue.text.split("\n");
      if (lines.length > maximumLines) {
        addError(key, `字幕は${maximumLines}行以内にしてください。`);
      }
      const overlongLine = lines.findIndex(
        (line) => Array.from(line).length > maximumCharacters
      );
      if (overlongLine !== -1) {
        addError(
          key,
          `${overlongLine + 1}行目は${maximumCharacters}文字以内にしてください。`
        );
      }
    }
    if (start === null) addError(key, "開始時刻は MM:SS.cc 形式で入力してください。");
    if (end === null) addError(key, "終了時刻は MM:SS.cc 形式で入力してください。");
    if (start !== null && (start < 0 || !Number.isFinite(start) || start > duration)) {
      addError(key, `開始時刻は0以上、動画尺 ${formatTime(duration)} 以内にしてください。`);
    }
    if (end !== null && (!Number.isFinite(end) || end > duration)) {
      addError(key, `終了時刻は動画尺 ${formatTime(duration)} 以内にしてください。`);
    }
    if (start !== null && end !== null) {
      if (end <= start) {
        addError(key, "終了時刻は開始時刻より後にしてください。");
      } else if (end - start < minimum) {
        addError(key, `字幕の長さは${minimum.toFixed(2)}秒以上にしてください。`);
      }
    }
  });

  for (let index = 1; index < values.length; index += 1) {
    const previous = values[index - 1];
    const current = values[index];
    if (
      previous.end !== null &&
      current.start !== null &&
      current.start < previous.end
    ) {
      addError(current.key, "直前の字幕と時間が重なっています。時刻または並び順を直してください。");
    }
  }
  return { valid: errors.size === 0, errors };
}

function applyTimingRaw(cue, field, rawValue) {
  const draft = timingDraft(cue);
  const rawKey = `${field}Raw`;
  const initialRawKey = field === "start" ? "initialStartRaw" : "initialEndRaw";
  const initialValueKey = field === "start" ? "initialStart" : "initialEnd";
  const touchedKey = `${field}Touched`;
  draft[rawKey] = rawValue;
  draft[touchedKey] = rawValue !== draft[initialRawKey];
  if (!draft[touchedKey]) {
    cue[field] = draft[initialValueKey];
  } else {
    const parsed = parseTime(rawValue);
    if (parsed !== null) cue[field] = roundCentisecond(parsed);
  }
  updateDirtyState();
}

function normalizeTimingInput(cue, field, input) {
  const draft = timingDraft(cue);
  const rawKey = `${field}Raw`;
  const parsed = parseTime(draft[rawKey]);
  if (parsed === null || !draft[`${field}Touched`]) return;
  input.value = formatTime(roundCentisecond(parsed));
  applyTimingRaw(cue, field, input.value);
}

function createTimingControl(cue, field, label, index, onStartChange) {
  const draft = timingDraft(cue);
  const fieldWrap = document.createElement("div");
  fieldWrap.className = "timing-field";

  const fieldLabel = document.createElement("label");
  fieldLabel.textContent = label;
  const input = document.createElement("input");
  input.type = "text";
  input.inputMode = "decimal";
  input.className = "timing-input";
  input.value = draft[`${field}Raw`];
  input.placeholder = "00:00.00";
  input.title = "↑↓で0.1秒、Shift＋↑↓で0.01秒調整";
  input.setAttribute("aria-label", `字幕 ${index + 1} ${label}時刻`);
  input.addEventListener("input", () => {
    applyTimingRaw(cue, field, input.value);
    if (field === "start") onStartChange();
  });
  input.addEventListener("blur", () => {
    normalizeTimingInput(cue, field, input);
    if (field === "start") onStartChange();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    const current = parseTime(input.value);
    if (current === null) return;
    const direction = event.key === "ArrowUp" ? 1 : -1;
    const increment = event.shiftKey ? 0.01 : 0.1;
    const next = roundCentisecond(current + direction * increment);
    const duration = Number(state.job?.duration_seconds);
    if (next < 0 || next > duration) return;
    event.preventDefault();
    input.value = formatTime(next);
    applyTimingRaw(cue, field, input.value);
    if (field === "start") onStartChange();
  });
  fieldLabel.append(input);

  const playheadButton = document.createElement("button");
  playheadButton.type = "button";
  playheadButton.className = "playhead-button";
  playheadButton.textContent = "再生位置";
  playheadButton.title = `現在の再生位置を${label}時刻に設定`;
  playheadButton.addEventListener("click", () => {
    const playhead = Number(elements.previewVideo.currentTime);
    if (!Number.isFinite(playhead)) return;
    input.value = formatTime(roundCentisecond(playhead));
    applyTimingRaw(cue, field, input.value);
    if (field === "start") onStartChange();
    input.focus();
  });

  fieldWrap.append(fieldLabel, playheadButton);
  return fieldWrap;
}

function renderCaptionRows() {
  elements.captionList.replaceChildren();
  state.caption.cues.forEach((cue, index) => {
    const key = cueKey(cue);
    const row = document.createElement("article");
    row.className = "caption-row";
    row.dataset.cueKey = key;

    const markerColumn = document.createElement("div");
    markerColumn.className = "caption-marker-column";
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = "time-marker";
    const updateMarker = () => {
      const start = timingValue(cue, "start");
      const label = start === null ? "時刻不正" : formatTime(start);
      marker.textContent = `${String(index + 1).padStart(2, "0")} · ${label}`;
      marker.title = start === null ? "開始時刻を直してください" : `${label}へ移動`;
    };
    updateMarker();
    marker.addEventListener("click", () => {
      const start = timingValue(cue, "start");
      if (start === null) return;
      elements.previewVideo.currentTime = start;
      paintLiveCaption(start);
      elements.previewVideo.focus();
    });
    markerColumn.append(marker);

    if (!cue.id) {
      const newBadge = document.createElement("span");
      newBadge.className = "new-caption-badge";
      newBadge.textContent = "新規";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "cancel-new-button";
      cancel.textContent = "追加を取消";
      cancel.addEventListener("click", () => {
        state.caption.cues.splice(index, 1);
        state.timingDrafts.delete(key);
        renderCaptionRows();
        updateDirtyState();
      });
      markerColumn.append(newBadge, cancel);
    }

    const textarea = document.createElement("textarea");
    textarea.className = "caption-text";
    textarea.rows = 2;
    textarea.value = cue.text;
    textarea.setAttribute("aria-label", `字幕 ${index + 1}`);
    textarea.addEventListener("input", () => {
      cue.text = textarea.value;
      updateDirtyState();
    });

    const timingEditor = document.createElement("div");
    timingEditor.className = "timing-editor";
    timingEditor.append(
      createTimingControl(cue, "start", "開始", index, updateMarker),
      createTimingControl(cue, "end", "終了", index, updateMarker)
    );

    const error = document.createElement("p");
    error.className = "inline-error caption-error";
    error.dataset.errorFor = key;
    error.setAttribute("role", "alert");
    error.hidden = true;

    row.append(markerColumn, textarea, timingEditor, error);
    elements.captionList.append(row);
  });
}

function updateDirtyState() {
  const dirty = isDirty();
  state.validation = state.caption
    ? validateCaptionDraft()
    : { valid: true, errors: new Map() };
  elements.dirtyBadge.hidden = !dirty;
  elements.previewNotice.hidden = !dirty;
  elements.saveButton.disabled = state.busy || !dirty || !state.validation.valid;
  elements.discardButton.disabled = state.busy || !dirty;
  elements.renderButton.disabled = state.busy || dirty || !state.validation.valid || !state.caption;
  elements.addCaptionButton.disabled = state.busy || !state.caption || !state.validation.valid;

  for (const row of elements.captionList.querySelectorAll(".caption-row")) {
    const messages = state.validation.errors.get(row.dataset.cueKey) || [];
    const error = row.querySelector(".caption-error");
    row.classList.toggle("is-dirty", state.caption.cues.some(
      (cue) => cueKey(cue) === row.dataset.cueKey && cueIsDirty(cue)
    ));
    row.classList.toggle("is-invalid", messages.length > 0);
    row.setAttribute("aria-invalid", messages.length ? "true" : "false");
    error.textContent = messages.join(" ");
    error.hidden = messages.length === 0;
  }
  refreshLiveCaption();
}

function setBusy(value) {
  state.busy = value;
  elements.jobSelect.disabled = value;
  elements.reloadButton.disabled = value;
  elements.renderSelect.disabled = value || elements.renderSelect.options.length <= 1;
  elements.stepBackButton.disabled = value || elements.previewVideo.hidden;
  elements.stepForwardButton.disabled = value || elements.previewVideo.hidden;
  elements.fullscreenButton.disabled = value || elements.previewVideo.hidden;
  for (const control of elements.captionList.querySelectorAll("input, textarea, button")) {
    control.disabled = value;
  }
  updateDirtyState();
}

function blockIfDirty() {
  if (!isDirty()) return false;
  elements.jobSelect.value = state.job?.job_id || "";
  showStatus(
    "未保存の字幕があります。保存するか「変更を破棄」してから切り替えてください。",
    "error"
  );
  return true;
}

async function waitForOperation(statusUrl) {
  const deadline = Date.now() + 12 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 750));
    const payload = await apiRequest(statusUrl);
    const operation = payload.operation;
    if (operation?.status === "complete") return operation.result || {};
    if (operation?.status === "failed") {
      const detail = operation.error;
      const message =
        typeof detail?.message === "string" && detail.message
          ? detail.message
          : "処理に失敗しました。logを確認してください。";
      const error = new Error(message);
      error.code = typeof detail?.code === "string" ? detail.code : "";
      throw error;
    }
  }
  throw new Error("処理の完了確認がtimeoutしました。");
}

async function adoptCandidateRange() {
  if (state.candidateBusy || !validateCandidateRange({ normalizeInputs: true })) return;
  const runId = candidateRunIdOf();
  const candidateId = state.candidateSelectedId;
  if (!runId || !candidateId) return;
  setCandidateBusy(true);
  elements.candidateAdoptStatus.textContent =
    "元動画を検証し、この範囲を文字起こししてショート編集を準備しています…";
  try {
    const payload = await apiRequest(candidateRunEndpoint("/adopt"), {
      method: "POST",
      mutation: true,
      body: {
        candidate_id: candidateId,
        start: state.candidateRange.start,
        end: state.candidateRange.end,
      },
    });
    const result = await waitForOperation(payload.status_url);
    if (!result?.project_id) throw new Error("ショート編集projectを確認できませんでした。");
    await loadCompositionProjects(result.project_id);
    switchMode("composition", { force: true });
    showStatus("選んだ範囲をショート編集へ追加しました。", "success");
  } catch (error) {
    elements.candidateAdoptStatus.textContent =
      "ショート編集への移行に失敗しました。候補結果と調整中の範囲は保持されています。";
    showStatus(error.message, "error");
  } finally {
    setCandidateBusy(false);
  }
}

async function saveCaptions() {
  state.validation = validateCaptionDraft();
  if (!isDirty() || state.busy || !state.validation.valid) return;
  setBusy(true);
  showStatus("新しい字幕revisionを保存しています…");
  try {
    const payload = await apiRequest(
      `/api/jobs/${encodeURIComponent(state.job.job_id)}/captions`,
      {
        method: "PUT",
        mutation: true,
        body: {
          base_revision: state.caption.revision,
          cues: state.caption.cues.map(({ id, start, end, text }) => ({
            id,
            start,
            end,
            text,
          })),
        },
      }
    );
    const result = await waitForOperation(payload.status_url);
    await loadJob(state.job.job_id);
    showStatus(`字幕v${result.revision || state.caption.revision}を保存しました。`, "success");
  } catch (error) {
    showStatus(
      error.code === "revision_conflict"
        ? "別画面で字幕が更新されました。下書きは保持しています。必要なら内容を控えてから変更を破棄・再読込してください。"
        : error.message,
      "error"
    );
  } finally {
    setBusy(false);
  }
}

async function createRender() {
  state.validation = state.caption
    ? validateCaptionDraft()
    : { valid: false, errors: new Map() };
  if (state.busy || isDirty() || !state.caption || !state.validation.valid) return;
  setBusy(true);
  showStatus(`字幕v${state.caption.revision}を固定してrenderを開始しました…`);
  try {
    const payload = await apiRequest(
      `/api/jobs/${encodeURIComponent(state.job.job_id)}/renders`,
      {
        method: "POST",
        mutation: true,
        body: { caption_revision: state.caption.revision },
      }
    );
    const result = await waitForOperation(payload.status_url);
    await loadJob(state.job.job_id, result.render_id || "");
    showStatus("preview renderが完了しました。", "success");
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function discardChanges() {
  state.caption.cues = snapshotCues(state.originalCues);
  initializeTimingDrafts();
  renderCaptionRows();
  updateDirtyState();
  elements.addCaptionError.hidden = true;
  showStatus("未保存の変更を破棄しました。");
}

function showAddCaptionError(message) {
  elements.addCaptionError.textContent = message;
  elements.addCaptionError.hidden = false;
}

function addCaptionAtPlayhead() {
  if (state.busy || !state.caption || !state.validation.valid) return;
  const duration = Number(state.job?.duration_seconds);
  const currentTime = Number(elements.previewVideo.currentTime);
  const start = roundCentisecond(Number.isFinite(currentTime) ? currentTime : 0);
  if (start < 0 || start > duration) {
    showAddCaptionError("現在の再生位置が動画の範囲外です。");
    return;
  }

  const insertionIndex = state.caption.cues.findIndex((cue) => {
    const cueStart = timingValue(cue, "start");
    return cueStart !== null && cueStart >= start;
  });
  const index = insertionIndex === -1 ? state.caption.cues.length : insertionIndex;
  const previous = index > 0 ? state.caption.cues[index - 1] : null;
  const next = index < state.caption.cues.length ? state.caption.cues[index] : null;
  const previousEnd = previous ? timingValue(previous, "end") : 0;
  const nextStart = next ? timingValue(next, "start") : duration;
  if (
    previousEnd === null ||
    nextStart === null ||
    start < previousEnd ||
    start >= nextStart
  ) {
    showAddCaptionError("現在の再生位置には字幕を追加できる空きがありません。");
    return;
  }

  const end = floorCentisecond(Math.min(start + 2, nextStart, duration));
  const minimum = minimumCueSeconds();
  if (end - start < minimum) {
    showAddCaptionError(
      `現在位置から次の字幕まで${minimum.toFixed(2)}秒以上の空きが必要です。`
    );
    return;
  }

  const cue = { id: null, start, end, text: "" };
  const key = cueKey(cue);
  state.timingDrafts.set(key, {
    startRaw: formatTime(start),
    endRaw: formatTime(end),
    initialStartRaw: formatTime(start),
    initialEndRaw: formatTime(end),
    initialStart: start,
    initialEnd: end,
    startTouched: false,
    endTouched: false,
  });
  state.caption.cues.splice(index, 0, cue);
  elements.addCaptionError.hidden = true;
  renderCaptionRows();
  updateDirtyState();
  const row = elements.captionList.querySelector(`[data-cue-key="${key}"]`);
  row?.scrollIntoView({ block: "center", behavior: "smooth" });
  row?.querySelector(".caption-text")?.focus();
}

function formatTime(value) {
  const centiseconds = Math.round(Math.max(0, Number(value) || 0) * 100);
  const minutes = Math.floor(centiseconds / 6000);
  const remainder = centiseconds % 6000;
  const seconds = Math.floor(remainder / 100);
  const fraction = remainder % 100;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(fraction).padStart(2, "0")}`;
}

function formatDuration(value) {
  if (!Number.isFinite(Number(value))) return "尺不明";
  return `${Number(value).toFixed(1)}秒`;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function compositionProjectId() {
  return state.composition?.project_id || "";
}

function compositionIsDirty() {
  return Boolean(
    state.compositionPlan &&
    state.originalCompositionPlan &&
    JSON.stringify(state.compositionPlan) !== JSON.stringify(state.originalCompositionPlan)
  );
}

function compositionBlockIfDirty() {
  if (!compositionIsDirty()) return false;
  elements.compositionProjectSelect.value = compositionProjectId();
  showStatus(
    "未保存の構成変更があります。保存するか「変更を破棄」してから切り替えてください。",
    "error"
  );
  return true;
}

function compositionTimeBase() {
  const source = state.composition?.source;
  const numerator = Number(source?.video_time_base_num);
  const denominator = Number(source?.video_time_base_den);
  return Number.isFinite(numerator) && Number.isFinite(denominator) && denominator > 0
    ? numerator / denominator
    : 0.001;
}

function compositionPtsSeconds(pts) {
  const source = state.composition?.source;
  const formatNumerator = Number(source?.format_start_time_num);
  const formatDenominator = Number(source?.format_start_time_den);
  const fallbackStart = Number(source?.video_start_pts || 0) * compositionTimeBase();
  const formatStart =
    Number.isFinite(formatNumerator) &&
    Number.isFinite(formatDenominator) &&
    formatDenominator > 0
      ? formatNumerator / formatDenominator
      : fallbackStart;
  return Number(pts) * compositionTimeBase() - formatStart;
}

function compositionFps() {
  const numerator = Number(state.composition?.compiled?.output?.fps_num || 30);
  const denominator = Number(state.composition?.compiled?.output?.fps_den || 1);
  return Number.isFinite(numerator) && Number.isFinite(denominator) && denominator > 0
    ? numerator / denominator
    : 30;
}

function compositionClipDuration(clip) {
  const fps = compositionFps();
  if (clip?.type === "generated_card") {
    return Number(clip.duration_frames || 0) / fps;
  }
  const exactFrames = Math.max(
    0,
    (Number(clip?.video_out_pts) - Number(clip?.video_in_pts)) *
      compositionTimeBase() *
      fps
  );
  return Math.floor(exactFrames + 0.5) / fps;
}

function compositionTimelineItems() {
  return Array.isArray(state.compositionPlan?.timeline_items)
    ? state.compositionPlan.timeline_items
    : [];
}

function selectedCompositionClip() {
  return compositionTimelineItems().find(
    (item) => item.id === state.compositionSelectedClipId
  ) || null;
}

function compositionBeatForClip(clip) {
  return (state.compositionPlan?.story_beats || []).find(
    (beat) => beat.id === clip?.story_beat_id
  ) || null;
}

function compositionCaptionsForClip(clipId) {
  return (state.compositionPlan?.speech_captions || []).filter(
    (caption) => caption.timeline_item_id === clipId
  );
}

function switchCompositionSection(section) {
  const buttons = [...document.querySelectorAll("[data-composition-section]")];
  const panels = [...document.querySelectorAll("[data-composition-panel]")];
  if (!buttons.some((button) => button.dataset.compositionSection === section)) return;
  state.compositionSection = section;
  for (const button of buttons) {
    const active = button.dataset.compositionSection === section;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  }
  for (const panel of panels) {
    panel.hidden = panel.dataset.compositionPanel !== section;
  }
  if (section === "captions") renderCompositionCaptionOverview();
}

function compositionCaptionClip(caption) {
  return compositionTimelineItems().find(
    (item) => item.id === caption?.timeline_item_id && item.type === "source_clip"
  ) || null;
}

function compositionCaptionLocalSeconds(caption, field) {
  const clip = compositionCaptionClip(caption);
  if (!clip) return 0;
  const pts = field === "start" ? caption.source_in_pts : caption.source_out_pts;
  return Math.max(0, (Number(pts) - Number(clip.video_in_pts)) * compositionTimeBase());
}

function compositionCaptionOutputSeconds(caption, field) {
  const segment = state.compositionLiveSegments.find(
    (value) => value.clipId === caption.timeline_item_id
  );
  return (segment?.outputStart || 0) + compositionCaptionLocalSeconds(caption, field);
}

function compositionCaptionMinimumPts() {
  return Math.max(1, Math.ceil((1 / compositionFps()) / compositionTimeBase()));
}

function sortCompositionCaptions() {
  const order = new Map(
    compositionTimelineItems().map((item, index) => [item.id, index])
  );
  state.compositionPlan.speech_captions.sort((left, right) =>
    (order.get(left.timeline_item_id) ?? 9999) -
      (order.get(right.timeline_item_id) ?? 9999) ||
    Number(left.source_in_pts) - Number(right.source_in_pts) ||
    String(left.id).localeCompare(String(right.id))
  );
}

function compositionCaptionValidation() {
  const captions = state.compositionPlan?.speech_captions || [];
  if (captions.length > 80) return "字幕は80件以内にしてください。";
  const seen = new Set();
  for (const caption of captions) {
    if (seen.has(caption.id)) return "字幕IDが重複しています。";
    seen.add(caption.id);
    if (typeof caption.text !== "string" || !caption.text.trim()) {
      return "空の字幕があります。本文を入力するか、その字幕を削除してください。";
    }
    if (caption.text.length > 500) return "字幕本文は500文字以内にしてください。";
    const clip = compositionCaptionClip(caption);
    if (!clip) return "カットに紐づかない字幕があります。";
    if (
      Number(caption.source_in_pts) < Number(clip.video_in_pts) ||
      Number(caption.source_out_pts) > Number(clip.video_out_pts) ||
      Number(caption.source_out_pts) - Number(caption.source_in_pts) < compositionCaptionMinimumPts()
    ) {
      return "字幕の表示時間がカット範囲外、または短すぎます。";
    }
  }
  for (const clip of compositionTimelineItems()) {
    const clipCaptions = compositionCaptionsForClip(clip.id).slice().sort(
      (left, right) => Number(left.source_in_pts) - Number(right.source_in_pts)
    );
    for (let index = 1; index < clipCaptions.length; index += 1) {
      if (Number(clipCaptions[index].source_in_pts) < Number(clipCaptions[index - 1].source_out_pts)) {
        return "同じカット内で字幕の表示時間が重なっています。";
      }
    }
  }
  return "";
}

function nextCompositionCaptionId() {
  const used = new Set([
    ...(state.compositionPlan?.story_beats || []).map((value) => value.id),
    ...compositionTimelineItems().map((value) => value.id),
    ...(state.compositionPlan?.presentation_events || []).map((value) => value.id),
    ...(state.compositionPlan?.speech_captions || []).map((value) => value.id),
    ...(state.compositionPlan?.editorial_overlays || []).map((value) => value.id),
    ...(state.compositionPlan?.join_edges || []).map((value) => value.id),
  ]);
  let ordinal = 1;
  while (used.has(`ui-caption-${String(ordinal).padStart(3, "0")}`)) ordinal += 1;
  return `ui-caption-${String(ordinal).padStart(3, "0")}`;
}

function showCompositionCaptionError(message) {
  elements.compositionCaptionError.textContent = message;
  elements.compositionCaptionError.hidden = !message;
  if (message) showStatus(message, "error");
}

function addCompositionCaption(clipId = state.compositionSelectedClipId) {
  const clip = compositionTimelineItems().find(
    (item) => item.id === clipId && item.type === "source_clip"
  );
  if (!clip) {
    showCompositionCaptionError("映像カットを選んでから字幕を追加してください。");
    return;
  }
  const minPts = compositionCaptionMinimumPts();
  const desiredDurationPts = Math.max(minPts, Math.round(1.5 / compositionTimeBase()));
  const segment = state.compositionLiveSegments[state.compositionLiveIndex];
  const playheadPts = segment?.clipId === clip.id
    ? Number(clip.video_in_pts) +
      Math.round((state.compositionLiveOutputTime - segment.outputStart) / compositionTimeBase())
    : Number(clip.video_in_pts);
  const existing = compositionCaptionsForClip(clip.id).slice().sort(
    (left, right) => Number(left.source_in_pts) - Number(right.source_in_pts)
  );
  const gaps = [];
  let cursor = Number(clip.video_in_pts);
  for (const caption of existing) {
    if (Number(caption.source_in_pts) - cursor >= minPts) {
      gaps.push([cursor, Number(caption.source_in_pts)]);
    }
    cursor = Math.max(cursor, Number(caption.source_out_pts));
  }
  if (Number(clip.video_out_pts) - cursor >= minPts) {
    gaps.push([cursor, Number(clip.video_out_pts)]);
  }
  const gap = gaps.find(([start, end]) => start <= playheadPts && playheadPts < end - minPts) ||
    gaps.find(([, end]) => playheadPts < end - minPts) || gaps[0];
  if (!gap) {
    showCompositionCaptionError("このカットには字幕を追加できる空き時間がありません。");
    return;
  }
  const start = Math.max(gap[0], Math.min(playheadPts, gap[1] - minPts));
  const end = Math.min(gap[1], start + desiredDurationPts);
  const caption = {
    id: nextCompositionCaptionId(),
    timeline_item_id: clip.id,
    source_in_pts: start,
    source_out_pts: end,
    text: "新しい字幕",
    role: "normal",
    token_ids: [],
  };
  state.compositionPlan.speech_captions.push(caption);
  sortCompositionCaptions();
  state.compositionSelectedClipId = clip.id;
  showCompositionCaptionError("");
  renderCompositionClipList();
  renderCompositionInspector();
  renderCompositionCaptionOverview();
  compositionDraftChanged({ preservePlayback: true });
  const field = document.querySelector(
    `[data-composition-caption-id="${caption.id}"] textarea`
  );
  field?.focus();
  field?.select();
}

function deleteCompositionCaption(captionId) {
  const before = state.compositionPlan.speech_captions.length;
  state.compositionPlan.speech_captions = state.compositionPlan.speech_captions.filter(
    (caption) => caption.id !== captionId
  );
  if (state.compositionPlan.speech_captions.length === before) return;
  showCompositionCaptionError("");
  renderCompositionClipList();
  renderCompositionInspector();
  renderCompositionCaptionOverview();
  compositionDraftChanged({ preservePlayback: true });
  showStatus("字幕を削除しました。保存前なら「変更を破棄」で戻せます。", "success");
}

function setCompositionCaptionBoundary(captionId, field, localSeconds) {
  const caption = state.compositionPlan.speech_captions.find(
    (value) => value.id === captionId
  );
  const clip = compositionCaptionClip(caption);
  if (!caption || !clip || !Number.isFinite(localSeconds)) {
    showCompositionCaptionError("字幕の時刻を数値で入力してください。");
    renderCompositionInspector();
    renderCompositionCaptionOverview();
    return;
  }
  const siblings = compositionCaptionsForClip(clip.id).slice().sort(
    (left, right) => Number(left.source_in_pts) - Number(right.source_in_pts)
  );
  const index = siblings.findIndex((value) => value.id === caption.id);
  const previous = index > 0 ? siblings[index - 1] : null;
  const next = index >= 0 && index < siblings.length - 1 ? siblings[index + 1] : null;
  const minPts = compositionCaptionMinimumPts();
  const target = Number(clip.video_in_pts) + Math.round(localSeconds / compositionTimeBase());
  const minimum = field === "start"
    ? Math.max(Number(clip.video_in_pts), Number(previous?.source_out_pts ?? clip.video_in_pts))
    : Number(caption.source_in_pts) + minPts;
  const maximum = field === "start"
    ? Number(caption.source_out_pts) - minPts
    : Math.min(Number(clip.video_out_pts), Number(next?.source_in_pts ?? clip.video_out_pts));
  if (target < minimum || target > maximum) {
    showCompositionCaptionError(
      "字幕はカット内に置き、前後の字幕と重ならない時刻にしてください。"
    );
    renderCompositionInspector();
    renderCompositionCaptionOverview();
    return;
  }
  if (field === "start") caption.source_in_pts = target;
  else caption.source_out_pts = target;
  sortCompositionCaptions();
  showCompositionCaptionError("");
  renderCompositionInspector();
  renderCompositionCaptionOverview();
  compositionDraftChanged({ preservePlayback: true });
}

function nudgeCompositionCaptionBoundary(captionId, field, delta) {
  const caption = state.compositionPlan.speech_captions.find(
    (value) => value.id === captionId
  );
  if (!caption) return;
  setCompositionCaptionBoundary(
    captionId,
    field,
    compositionCaptionLocalSeconds(caption, field) + delta
  );
}

function openCompositionCaptionInVideo(caption) {
  const outputTime = compositionCaptionOutputSeconds(caption, "start");
  switchCompositionSection("cuts");
  selectCompositionClip(caption.timeline_item_id, { seek: false });
  showCompositionLivePreview({ preserveTime: true });
  setCompositionLiveOutputTime(outputTime);
  elements.compositionSourceVideo.currentTime = Math.max(
    0,
    compositionPtsSeconds(caption.source_in_pts)
  );
}

function createCompositionCaptionEditor(caption, { overview = false } = {}) {
  const row = document.createElement("article");
  row.className = `composition-caption-editor${overview ? " is-overview" : ""}`;
  row.dataset.compositionCaptionId = caption.id;

  const heading = document.createElement("div");
  heading.className = "composition-caption-editor-heading";
  const time = document.createElement("span");
  time.className = "composition-caption-output-time";
  time.textContent = overview
    ? `${compositionLiveTimeLabel(compositionCaptionOutputSeconds(caption, "start"))} → ${compositionLiveTimeLabel(compositionCaptionOutputSeconds(caption, "end"))}`
    : `カット内 ${compositionCaptionLocalSeconds(caption, "start").toFixed(1)} → ${compositionCaptionLocalSeconds(caption, "end").toFixed(1)}秒`;
  const actions = document.createElement("div");
  actions.className = "composition-caption-editor-actions";
  if (overview) {
    const preview = document.createElement("button");
    preview.type = "button";
    preview.textContent = "映像で確認";
    preview.addEventListener("click", () => openCompositionCaptionInVideo(caption));
    actions.append(preview);
  }
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "is-danger";
  remove.textContent = "削除";
  remove.addEventListener("click", () => deleteCompositionCaption(caption.id));
  actions.append(remove);
  heading.append(time, actions);

  const textarea = document.createElement("textarea");
  textarea.value = caption.text;
  textarea.maxLength = 500;
  textarea.setAttribute("aria-label", "字幕テキスト");
  textarea.addEventListener("input", () => {
    caption.text = textarea.value;
    renderCompositionClipList();
    compositionDraftChanged({ preservePlayback: true });
  });

  const settings = document.createElement("div");
  settings.className = "composition-caption-settings";
  const roleLabel = document.createElement("label");
  roleLabel.innerHTML = "<span>見せ方</span>";
  const role = document.createElement("select");
  role.setAttribute("aria-label", "字幕の役割");
  for (const [value, label] of [
    ["normal", "通常"],
    ["emphasis", "強調"],
    ["quote", "引用"],
    ["comment", "コメント"],
  ]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    role.append(option);
  }
  role.value = caption.role;
  role.addEventListener("change", () => {
    caption.role = role.value;
    compositionDraftChanged({ preservePlayback: true });
  });
  roleLabel.append(role);
  settings.append(roleLabel);

  for (const [field, label] of [["start", "開始"], ["end", "終了"]]) {
    const timing = document.createElement("div");
    timing.className = "composition-caption-timing-control";
    const timingLabel = document.createElement("label");
    const labelText = document.createElement("span");
    labelText.textContent = `${label}（カット内）`;
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.max = String(compositionClipDuration(compositionCaptionClip(caption)));
    input.step = "0.1";
    input.value = compositionCaptionLocalSeconds(caption, field).toFixed(2);
    input.setAttribute("aria-label", `${label}時刻（カット内秒）`);
    input.addEventListener("change", () => {
      setCompositionCaptionBoundary(caption.id, field, Number(input.value));
    });
    timingLabel.append(labelText, input);
    timing.append(timingLabel);
    for (const delta of [-0.1, 0.1]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${delta < 0 ? "−" : "＋"}0.1`;
      button.setAttribute("aria-label", `${label}を${delta < 0 ? "0.1秒早める" : "0.1秒遅らせる"}`);
      button.addEventListener("click", () =>
        nudgeCompositionCaptionBoundary(caption.id, field, delta)
      );
      timing.append(button);
    }
    settings.append(timing);
  }
  row.append(heading, textarea, settings);
  return row;
}

function renderCompositionCaptionOverview() {
  const captions = state.compositionPlan?.speech_captions || [];
  elements.compositionCaptionOverviewCount.textContent = `${captions.length}件`;
  elements.compositionCaptionOverviewEmpty.hidden = captions.length > 0;
  elements.compositionCaptionOverviewList.replaceChildren();
  for (const [index, clip] of compositionTimelineItems().entries()) {
    if (clip.type !== "source_clip") continue;
    const group = document.createElement("section");
    group.className = "composition-caption-group";
    const heading = document.createElement("div");
    heading.className = "composition-caption-group-heading";
    const identity = document.createElement("div");
    const beat = compositionBeatForClip(clip);
    const label = document.createElement("strong");
    label.textContent = `${index + 1}. ${beat?.role || "scene"}`;
    const summary = document.createElement("span");
    summary.textContent = compositionCaptionsForClip(clip.id)[0]?.text || "字幕なし";
    identity.append(label, summary);
    const controls = document.createElement("div");
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "カットを開く";
    open.addEventListener("click", () => {
      switchCompositionSection("cuts");
      selectCompositionClip(clip.id, { seek: true });
    });
    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "＋ 字幕";
    add.addEventListener("click", () => addCompositionCaption(clip.id));
    controls.append(open, add);
    heading.append(identity, controls);
    group.append(heading);
    const clipCaptions = compositionCaptionsForClip(clip.id);
    if (!clipCaptions.length) {
      const empty = document.createElement("p");
      empty.className = "composition-caption-group-empty";
      empty.textContent = "このカットには字幕がありません。";
      group.append(empty);
    } else {
      for (const caption of clipCaptions) {
        group.append(createCompositionCaptionEditor(caption, { overview: true }));
      }
    }
    elements.compositionCaptionOverviewList.append(group);
  }
}

function compositionLayoutForClip(clipId) {
  const values = (state.compositionPlan?.presentation_events || [])
    .filter((event) => event.timeline_item_id === clipId)
    .map((event) => event.layout);
  return values.length && values.every((value) => value === values[0])
    ? values[0]
    : "mixed";
}

function rebuildCompositionJoins() {
  const items = compositionTimelineItems();
  const existingByPair = new Map(
    (state.compositionPlan?.join_edges || []).map((edge) => [
      `${edge.from_item_id}\u0000${edge.to_item_id}`,
      edge,
    ])
  );
  const used = new Set([
    ...(state.compositionPlan?.story_beats || []).map((value) => value.id),
    ...items.map((value) => value.id),
    ...(state.compositionPlan?.presentation_events || []).map((value) => value.id),
    ...(state.compositionPlan?.speech_captions || []).map((value) => value.id),
    ...(state.compositionPlan?.editorial_overlays || []).map((value) => value.id),
    ...(state.compositionPlan?.join_edges || []).map((value) => value.id),
  ]);
  const joins = [];
  for (let index = 0; index < items.length - 1; index += 1) {
    const fromItemId = items[index].id;
    const toItemId = items[index + 1].id;
    const existing = existingByPair.get(`${fromItemId}\u0000${toItemId}`);
    if (existing) {
      joins.push(cloneJson(existing));
      continue;
    }
    let suffix = index + 1;
    let id = `ui-join-${String(suffix).padStart(2, "0")}`;
    while (used.has(id)) {
      suffix += 1;
      id = `ui-join-${String(suffix).padStart(2, "0")}`;
    }
    used.add(id);
    joins.push({
      id,
      from_item_id: fromItemId,
      to_item_id: toItemId,
      audio_transition: "micro_fade",
    });
  }
  state.compositionPlan.join_edges = joins;
}

function updateCompositionBeatItems() {
  const items = compositionTimelineItems();
  const order = items.map((item) => item.id);
  for (const beat of state.compositionPlan.story_beats || []) {
    beat.timeline_item_ids = order.filter((id) =>
      items.some((item) => item.id === id && item.story_beat_id === beat.id)
    );
  }
  state.compositionPlan.story_beats = state.compositionPlan.story_beats.filter(
    (beat) => beat.timeline_item_ids.length
  );
}

function setCompositionBusy(value) {
  state.compositionBusy = value;
  elements.compositionProjectSelect.disabled = value;
  elements.compositionReloadButton.disabled = value;
  elements.compositionRenderSelect.disabled = value;
  elements.compositionLivePlayButton.disabled = value;
  elements.compositionLiveSeek.disabled = value;
  elements.compositionKeepVisibleButton.disabled = value;
  for (const control of elements.compositionWorkspace.querySelectorAll(
    ".composition-clip-card, .composition-inspector-panel button, .composition-inspector-panel textarea, .composition-inspector-panel select, .composition-caption-overview button, .composition-caption-overview textarea, .composition-caption-overview select, .composition-caption-overview input"
  )) {
    control.disabled = value;
  }
  updateCompositionDirtyState();
}

function updateCompositionDirtyState() {
  const dirty = compositionIsDirty();
  const validationMessage = state.compositionPlan ? compositionCaptionValidation() : "";
  const valid = !validationMessage;
  elements.compositionDirtyBadge.hidden = !dirty;
  elements.compositionValidationMessage.textContent = validationMessage;
  elements.compositionValidationMessage.hidden = valid;
  elements.compositionSaveButton.disabled = state.compositionBusy || !dirty || !valid;
  elements.compositionDiscardButton.disabled = state.compositionBusy || !dirty;
  elements.compositionRenderButton.disabled =
    state.compositionBusy || dirty || !valid || !state.composition?.edit?.revision;
}

function compositionLiveTimeLabel(value) {
  const tenths = Math.max(0, Math.round((Number(value) || 0) * 10));
  const minutes = Math.floor(tenths / 600);
  const seconds = Math.floor((tenths % 600) / 10);
  const fraction = tenths % 10;
  return `${minutes}:${String(seconds).padStart(2, "0")}.${fraction}`;
}

function rebuildCompositionLiveSegments() {
  let outputCursor = 0;
  state.compositionLiveSegments = compositionTimelineItems().map((item) => {
    const duration = compositionClipDuration(item);
    const segment = {
      item,
      clipId: item.id,
      outputStart: outputCursor,
      outputEnd: outputCursor + duration,
      duration,
      sourceStart: item.type === "source_clip" ? compositionPtsSeconds(item.video_in_pts) : null,
      sourceEnd: item.type === "source_clip" ? compositionPtsSeconds(item.video_out_pts) : null,
    };
    outputCursor += duration;
    return segment;
  });
  elements.compositionLiveSeek.max = String(outputCursor);
  return outputCursor;
}

function compositionLiveDuration() {
  return state.compositionLiveSegments.at(-1)?.outputEnd || 0;
}

function compositionLiveSegmentIndexAt(outputTime) {
  const segments = state.compositionLiveSegments;
  if (!segments.length) return -1;
  const clamped = Math.max(0, Math.min(compositionLiveDuration(), Number(outputTime) || 0));
  const index = segments.findIndex((segment) => clamped < segment.outputEnd - 0.0005);
  return index >= 0 ? index : segments.length - 1;
}

function compositionLiveOutputStartForClip(clipId) {
  return state.compositionLiveSegments.find((segment) => segment.clipId === clipId)?.outputStart;
}

function updateCompositionLiveControls() {
  const duration = compositionLiveDuration();
  const current = Math.max(0, Math.min(duration, state.compositionLiveOutputTime || 0));
  elements.compositionLiveSeek.value = String(current);
  elements.compositionLiveTime.textContent =
    `${compositionLiveTimeLabel(current)} / ${compositionLiveTimeLabel(duration)}`;
  elements.compositionLivePlayButton.textContent = state.compositionLivePlaying ? "❚❚" : "▶";
  elements.compositionLivePlayButton.setAttribute(
    "aria-label",
    state.compositionLivePlaying
      ? "ライブ編集プレビューを一時停止"
      : "ライブ編集プレビューを再生"
  );
}

function compositionDrawCover(ctx, video, region, target) {
  const sourceWidth = Number(video.videoWidth);
  const sourceHeight = Number(video.videoHeight);
  if (!(sourceWidth > 0 && sourceHeight > 0)) return false;
  const normalized = Array.isArray(region) && region.length === 4
    ? region.map((value) => Number(value) / 1000000)
    : [0, 0, 1, 1];
  let sourceX = Math.max(0, Math.min(1, normalized[0])) * sourceWidth;
  let sourceY = Math.max(0, Math.min(1, normalized[1])) * sourceHeight;
  let cropWidth = Math.max(
    1 / sourceWidth,
    Math.min(1 - normalized[0], normalized[2])
  ) * sourceWidth;
  let cropHeight = Math.max(
    1 / sourceHeight,
    Math.min(1 - normalized[1], normalized[3])
  ) * sourceHeight;
  const targetAspect = target.width / target.height;
  const sourceAspect = cropWidth / cropHeight;
  if (sourceAspect > targetAspect) {
    const nextWidth = cropHeight * targetAspect;
    sourceX += (cropWidth - nextWidth) / 2;
    cropWidth = nextWidth;
  } else {
    const nextHeight = cropWidth / targetAspect;
    sourceY += (cropHeight - nextHeight) / 2;
    cropHeight = nextHeight;
  }
  ctx.drawImage(
    video,
    sourceX,
    sourceY,
    cropWidth,
    cropHeight,
    target.x,
    target.y,
    target.width,
    target.height
  );
  return true;
}

function compositionDrawContain(ctx, video, target) {
  const sourceWidth = Number(video.videoWidth);
  const sourceHeight = Number(video.videoHeight);
  if (!(sourceWidth > 0 && sourceHeight > 0)) return false;
  const scale = Math.min(target.width / sourceWidth, target.height / sourceHeight);
  const width = sourceWidth * scale;
  const height = sourceHeight * scale;
  ctx.drawImage(
    video,
    target.x + (target.width - width) / 2,
    target.y + (target.height - height) / 2,
    width,
    height
  );
  return true;
}

function compositionDrawTextBlock(
  ctx,
  text,
  { x, y, maxWidth, fontSize, color, stroke, align = "center", baseline = "middle" }
) {
  const lines = String(text || "").split(/\r?\n/).filter((line) => line.length);
  if (!lines.length) return;
  let size = fontSize;
  ctx.textAlign = align;
  ctx.textBaseline = baseline;
  ctx.lineJoin = "round";
  while (size > 18) {
    ctx.font = `900 ${size}px "Yu Gothic UI", "Meiryo", sans-serif`;
    if (Math.max(...lines.map((line) => ctx.measureText(line).width)) <= maxWidth) break;
    size -= 2;
  }
  const lineHeight = size * 1.2;
  const firstY = y - ((lines.length - 1) * lineHeight) / 2;
  for (const [index, line] of lines.entries()) {
    const lineY = firstY + index * lineHeight;
    ctx.lineWidth = Math.max(5, size * 0.14);
    ctx.strokeStyle = stroke;
    ctx.strokeText(line, x, lineY, maxWidth);
    ctx.fillStyle = color;
    ctx.fillText(line, x, lineY, maxWidth);
  }
}

function compositionLiveLayoutForFrame(segment, sourcePts) {
  if (segment.item.type === "generated_card") return "generated_card";
  const event = (state.compositionPlan?.presentation_events || []).find(
    (value) =>
      value.timeline_item_id === segment.clipId &&
      Number(value.source_in_pts) <= sourcePts &&
      sourcePts < Number(value.source_out_pts)
  );
  return event?.layout || compositionLayoutForClip(segment.clipId) || "standard";
}

function drawCompositionLivePreview() {
  const canvas = elements.compositionLiveCanvas;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, width, height);
  const segment = state.compositionLiveSegments[state.compositionLiveIndex];
  if (!segment) {
    compositionDrawTextBlock(ctx, "プレビューできるカットがありません", {
      x: width / 2,
      y: height / 2,
      maxWidth: width - 60,
      fontSize: 24,
      color: "#c6ced8",
      stroke: "#000",
    });
    updateCompositionLiveControls();
    return;
  }
  const localTime = Math.max(
    0,
    Math.min(segment.duration, state.compositionLiveOutputTime - segment.outputStart)
  );
  const sourcePts = segment.item.type === "source_clip"
    ? Number(segment.item.video_in_pts) + localTime / compositionTimeBase()
    : null;
  if (segment.item.type === "generated_card") {
    compositionDrawTextBlock(ctx, segment.item.text || "", {
      x: width / 2,
      y: height / 2,
      maxWidth: width - 70,
      fontSize: 44,
      color: "#fff",
      stroke: "#111",
    });
  } else {
    const video = elements.compositionLiveSource;
    const layout = compositionLiveLayoutForFrame(segment, sourcePts);
    const regions = state.compositionPlan?.source_regions || {};
    const full = { x: 0, y: 0, width, height };
    let drawn = false;
    if (video.readyState >= 2) {
      if (layout === "split") {
        drawn = compositionDrawCover(ctx, video, regions.content, {
          x: 0,
          y: 0,
          width,
          height: height / 2,
        });
        drawn = compositionDrawCover(ctx, video, regions.person, {
          x: 0,
          y: height / 2,
          width,
          height: height / 2,
        }) || drawn;
      } else if (["content", "person", "comment"].includes(layout)) {
        drawn = compositionDrawCover(ctx, video, regions[layout], full);
      } else {
        ctx.save();
        ctx.filter = "blur(18px) brightness(0.72) saturate(0.85)";
        drawn = compositionDrawCover(ctx, video, [0, 0, 1000000, 1000000], {
          x: -18,
          y: -18,
          width: width + 36,
          height: height + 36,
        });
        ctx.restore();
        compositionDrawContain(ctx, video, full);
      }
    }
    if (!drawn) {
      compositionDrawTextBlock(ctx, "映像を読み込み中…", {
        x: width / 2,
        y: height / 2,
        maxWidth: width - 60,
        fontSize: 24,
        color: "#c6ced8",
        stroke: "#000",
      });
    }
  }

  const localFrame = Math.floor(localTime * compositionFps());
  const overlays = (state.compositionPlan?.editorial_overlays || []).filter(
    (overlay) =>
      overlay.timeline_item_id === segment.clipId &&
      Number(overlay.local_in_frame) <= localFrame &&
      localFrame < Number(overlay.local_out_frame)
  );
  if (segment.item.type === "generated_card" && !overlays.length) {
    overlays.push({ kind: "chapter_card", text: segment.item.text || "" });
  }
  for (const overlay of overlays) {
    if (overlay.kind === "chapter_card") continue;
    const isComment = overlay.kind === "comment_card";
    compositionDrawTextBlock(ctx, overlay.text, {
      x: width / 2,
      y: isComment ? 150 : 72,
      maxWidth: width - 60,
      fontSize: isComment ? 29 : 26,
      color: isComment ? "#fff2a8" : "#fff",
      stroke: isComment ? "#332111" : "#111",
    });
  }

  const captions = segment.item.type === "source_clip"
    ? compositionCaptionsForClip(segment.clipId).filter(
        (caption) =>
          Number(caption.source_in_pts) <= sourcePts &&
          sourcePts < Number(caption.source_out_pts)
      )
    : [];
  for (const caption of captions) {
    const emphasis = caption.role === "emphasis";
    const comment = caption.role === "comment";
    const quote = caption.role === "quote";
    compositionDrawTextBlock(ctx, caption.text, {
      x: width / 2,
      y: emphasis ? height / 2 : comment ? 155 : height - 205,
      maxWidth: width - 72,
      fontSize: emphasis ? 39 : comment ? 29 : 31,
      color: emphasis ? "#ff4d4d" : comment ? "#fff2a8" : quote ? "#66e6ff" : "#fff",
      stroke: emphasis ? "#fff" : "#111",
    });
  }
  updateCompositionLiveControls();
}

function cancelCompositionLiveFrame() {
  if (state.compositionLiveFrameRequest !== null) {
    cancelAnimationFrame(state.compositionLiveFrameRequest);
    state.compositionLiveFrameRequest = null;
  }
}

function pauseCompositionLivePreview() {
  state.compositionLivePlaying = false;
  state.compositionLiveGeneratedStartedAt = null;
  elements.compositionLiveSource.pause();
  cancelCompositionLiveFrame();
  updateCompositionLiveControls();
}

function scheduleCompositionLiveFrame() {
  cancelCompositionLiveFrame();
  if (state.compositionLivePlaying) {
    state.compositionLiveFrameRequest = requestAnimationFrame(paintCompositionLiveFrame);
  }
}

function setCompositionLiveOutputTime(outputTime, { keepPlaying = false } = {}) {
  if (keepPlaying) {
    state.compositionLivePlaying = true;
  } else {
    state.compositionLivePlaying = false;
    state.compositionLiveGeneratedStartedAt = null;
    cancelCompositionLiveFrame();
  }
  const duration = compositionLiveDuration();
  const clamped = Math.max(0, Math.min(duration, Number(outputTime) || 0));
  const index = compositionLiveSegmentIndexAt(clamped);
  state.compositionLiveOutputTime = clamped;
  state.compositionLiveIndex = Math.max(0, index);
  const segment = state.compositionLiveSegments[index];
  if (!segment) {
    pauseCompositionLivePreview();
    drawCompositionLivePreview();
    return;
  }
  const localTime = Math.max(0, Math.min(segment.duration, clamped - segment.outputStart));
  if (segment.item.type === "source_clip") {
    state.compositionLiveGeneratedStartedAt = null;
    const target = segment.sourceStart + localTime;
    if (Number.isFinite(target) && Math.abs(elements.compositionLiveSource.currentTime - target) > 0.025) {
      elements.compositionLiveSource.currentTime = target;
    }
    if (keepPlaying) {
      elements.compositionLiveSource.play().catch(() => {
        pauseCompositionLivePreview();
        showStatus("ライブプレビューを再生できませんでした。もう一度再生を押してください。", "error");
      });
    } else {
      elements.compositionLiveSource.pause();
    }
  } else {
    elements.compositionLiveSource.pause();
    state.compositionLiveGeneratedStartedAt = keepPlaying
      ? performance.now() - localTime * 1000
      : null;
  }
  drawCompositionLivePreview();
  if (keepPlaying) scheduleCompositionLiveFrame();
}

function advanceCompositionLiveSegment() {
  const next = state.compositionLiveIndex + 1;
  if (next >= state.compositionLiveSegments.length) {
    const duration = compositionLiveDuration();
    pauseCompositionLivePreview();
    state.compositionLiveOutputTime = duration;
    drawCompositionLivePreview();
    return;
  }
  setCompositionLiveOutputTime(state.compositionLiveSegments[next].outputStart, {
    keepPlaying: true,
  });
}

function paintCompositionLiveFrame(timestamp) {
  state.compositionLiveFrameRequest = null;
  if (!state.compositionLivePlaying) return;
  const segment = state.compositionLiveSegments[state.compositionLiveIndex];
  if (!segment) {
    pauseCompositionLivePreview();
    return;
  }
  if (segment.item.type === "generated_card") {
    if (state.compositionLiveGeneratedStartedAt === null) {
      state.compositionLiveGeneratedStartedAt = timestamp;
    }
    const localTime = (timestamp - state.compositionLiveGeneratedStartedAt) / 1000;
    if (localTime >= segment.duration - 0.001) {
      advanceCompositionLiveSegment();
      return;
    }
    state.compositionLiveOutputTime = segment.outputStart + localTime;
  } else if (!elements.compositionLiveSource.seeking) {
    const localTime = Math.max(0, elements.compositionLiveSource.currentTime - segment.sourceStart);
    if (localTime >= segment.duration - 0.025) {
      advanceCompositionLiveSegment();
      return;
    }
    state.compositionLiveOutputTime = segment.outputStart + localTime;
  }
  drawCompositionLivePreview();
  scheduleCompositionLiveFrame();
}

function playCompositionLivePreview() {
  if (state.compositionPreviewMode !== "live") return;
  if (!state.compositionLiveSegments.length) return;
  elements.compositionSourceVideo.pause();
  elements.compositionPreviewVideo.pause();
  if (state.compositionLiveOutputTime >= compositionLiveDuration() - 0.001) {
    state.compositionLiveOutputTime = 0;
  }
  state.compositionLivePlaying = true;
  updateCompositionLiveControls();
  setCompositionLiveOutputTime(state.compositionLiveOutputTime, { keepPlaying: true });
}

function showCompositionLivePreview({ seekClipId = "", preserveTime = true } = {}) {
  state.compositionPreviewMode = "live";
  state.compositionSelectedRenderId = "";
  elements.compositionOutputShell.classList.add("is-live");
  elements.compositionPreviewVideo.pause();
  elements.compositionPreviewVideo.hidden = true;
  elements.compositionLiveCanvas.hidden = false;
  elements.compositionLiveControls.hidden = false;
  elements.compositionRenderIdentity.textContent = compositionIsDirty()
    ? "ライブ編集 · 未保存を反映"
    : "ライブ編集 · 現在のRevision";
  if (elements.compositionRenderSelect.options.length) {
    elements.compositionRenderSelect.value = "live";
  }
  const duration = rebuildCompositionLiveSegments();
  elements.compositionPreviewEmpty.hidden = duration > 0;
  let target = preserveTime ? state.compositionLiveOutputTime : 0;
  if (seekClipId) {
    target = compositionLiveOutputStartForClip(seekClipId) ?? target;
  }
  setCompositionLiveOutputTime(Math.min(target, duration));
}

function compositionDraftChanged({ seekSelected = false, preservePlayback = false } = {}) {
  const wasPlaying = preservePlayback && state.compositionLivePlaying;
  const previousTime = state.compositionLiveOutputTime;
  pauseCompositionLivePreview();
  rebuildCompositionLiveSegments();
  showCompositionLivePreview({
    seekClipId: seekSelected ? state.compositionSelectedClipId : "",
    preserveTime: !seekSelected,
  });
  if (!seekSelected) setCompositionLiveOutputTime(previousTime, { keepPlaying: wasPlaying });
  updateCompositionDirtyState();
}

async function loadCompositionProjects(preferredProjectId = "") {
  const payload = await apiRequest("/api/compositions");
  state.compositionProjects = Array.isArray(payload.projects) ? payload.projects : [];
  elements.compositionProjectSelect.replaceChildren();
  for (const project of state.compositionProjects) {
    const option = document.createElement("option");
    option.value = project.project_id;
    option.textContent = `${project.project_id} · Revision ${project.current_revision ?? "—"}`;
    elements.compositionProjectSelect.append(option);
  }
  if (!elements.compositionProjectSelect.options.length) {
    state.composition = null;
    state.compositionPlan = null;
    state.originalCompositionPlan = null;
    elements.compositionContent.hidden = true;
    elements.compositionEmpty.hidden = false;
    elements.compositionModeButton.disabled = false;
    return;
  }
  elements.compositionEmpty.hidden = true;
  elements.compositionContent.hidden = false;
  elements.compositionModeButton.disabled = false;
  const selected = state.compositionProjects.some(
    (project) => project.project_id === preferredProjectId
  )
    ? preferredProjectId
    : elements.compositionProjectSelect.value;
  elements.compositionProjectSelect.value = selected;
  await loadComposition(selected);
}

async function loadComposition(projectId, preferredRenderId = "") {
  setCompositionBusy(true);
  hideStatus();
  try {
    pauseCompositionLivePreview();
    const payload = await apiRequest(`/api/compositions/${encodeURIComponent(projectId)}`);
    const composition = payload.composition;
    if (!composition?.edit?.plan || !Array.isArray(composition.edit.plan.timeline_items)) {
      throw new Error("Composition artifactの形式が不正です。");
    }
    state.composition = composition;
    state.compositionPlan = cloneJson(composition.edit.plan);
    state.originalCompositionPlan = cloneJson(composition.edit.plan);
    state.compositionSelectedClipId = composition.edit.plan.timeline_items.some(
      (item) => item.id === state.compositionSelectedClipId
    )
      ? state.compositionSelectedClipId
      : composition.edit.plan.timeline_items[0]?.id || "";
    const source = composition.source;
    elements.compositionSourceStage.style.aspectRatio = `${source.width} / ${source.height}`;
    const sourceUrl = `/api/compositions/${encodeURIComponent(projectId)}/source/video`;
    elements.compositionSourceVideo.src = sourceUrl;
    elements.compositionLiveSource.src = sourceUrl;
    state.compositionPreviewMode = preferredRenderId ? "render" : "live";
    state.compositionSelectedRenderId = preferredRenderId || "";
    state.compositionLiveOutputTime = 0;
    renderCompositionWorkspace(preferredRenderId);
    selectCompositionClip(state.compositionSelectedClipId, { seek: true });
  } finally {
    setCompositionBusy(false);
  }
}

function renderCompositionWorkspace(preferredRenderId = "") {
  const revision = Number(state.composition?.edit?.revision);
  const total = compositionTimelineItems().reduce(
    (sum, item) => sum + compositionClipDuration(item),
    0
  );
  elements.compositionRevisionBadge.textContent = `Revision ${revision || "—"}`;
  elements.compositionDurationBadge.textContent = `${total.toFixed(1)}秒 · ${compositionTimelineItems().length}カット`;
  renderCompositionClipList();
  renderCompositionInspector();
  renderCompositionCaptionOverview();
  renderCompositionCropRect();
  rebuildCompositionLiveSegments();
  const renders = Array.isArray(state.composition?.renders) ? state.composition.renders : [];
  elements.compositionRenderSelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "live";
  placeholder.textContent = compositionIsDirty()
    ? "ライブ編集 · 未保存を反映"
    : "ライブ編集 · 現在のRevision";
  elements.compositionRenderSelect.append(placeholder);
  for (const render of renders.slice().reverse()) {
    const option = document.createElement("option");
    option.value = render.render_id;
    const stale = compositionIsDirty()
      ? " · 未保存は未反映"
      : render.edit_revision !== revision
        ? " · 前版"
        : "";
    option.textContent = `${render.render_profile} · Revision ${render.edit_revision}${stale}`;
    elements.compositionRenderSelect.append(option);
  }
  const requestedRenderId = preferredRenderId || state.compositionSelectedRenderId;
  const selected = state.compositionPreviewMode === "render"
    ? renders.find((render) => render.render_id === requestedRenderId) || null
    : null;
  if (!selected) {
    state.compositionPreviewMode = "live";
    state.compositionSelectedRenderId = "";
  }
  elements.compositionRenderSelect.value = selected?.render_id || "live";
  updateCompositionPreview(selected);
  switchCompositionSection(state.compositionSection);
  updateCompositionDirtyState();
}

function updateCompositionPreview(render) {
  if (!render?.render_id || !compositionProjectId()) {
    showCompositionLivePreview({ preserveTime: true });
    return;
  }
  pauseCompositionLivePreview();
  state.compositionPreviewMode = "render";
  state.compositionSelectedRenderId = render.render_id;
  elements.compositionOutputShell.classList.remove("is-live");
  elements.compositionLiveCanvas.hidden = true;
  elements.compositionLiveControls.hidden = true;
  elements.compositionPreviewVideo.hidden = false;
  elements.compositionPreviewEmpty.hidden = true;
  const project = encodeURIComponent(compositionProjectId());
  const renderId = encodeURIComponent(render.render_id);
  elements.compositionPreviewVideo.src = `/api/compositions/${project}/renders/${renderId}/video`;
  const renderLabel = render.render_profile === "final" ? "保存済みFinal" : "保存済みProxy";
  elements.compositionRenderIdentity.textContent = compositionIsDirty()
    ? `${renderLabel} · Revision ${render.edit_revision} · 未保存変更は未反映`
    : render.edit_revision !== state.composition.edit.revision
      ? `${renderLabel} · Revision ${render.edit_revision} · 前版`
      : `${renderLabel} · Revision ${render.edit_revision}`;
}

function clearCompositionPreview() {
  pauseCompositionLivePreview();
  if (!compositionProjectId()) {
    elements.compositionPreviewVideo.pause();
    elements.compositionPreviewVideo.removeAttribute("src");
    elements.compositionPreviewVideo.load();
    elements.compositionPreviewVideo.hidden = true;
    elements.compositionPreviewEmpty.hidden = false;
    elements.compositionRenderIdentity.textContent = "render未選択";
  }
}

function compositionClipSummary(clip) {
  const captionText = compositionCaptionsForClip(clip.id)
    .map((caption) => String(caption.text || "").replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join(" / ");
  if (captionText) return captionText;
  const overlay = (state.compositionPlan?.editorial_overlays || []).find(
    (value) => value.timeline_item_id === clip.id
  );
  return overlay?.text || (clip.type === "generated_card" ? clip.text : "映像・間");
}

function renderCompositionClipList() {
  elements.compositionClipList.replaceChildren();
  const roleLabels = {
    hook: "HOOK",
    setup: "SETUP",
    development: "展開",
    reaction: "REACTION",
    payoff: "PAYOFF",
    aftertaste: "余韻",
  };
  const items = compositionTimelineItems();
  for (const [index, clip] of items.entries()) {
    const beat = compositionBeatForClip(clip);
    const card = document.createElement("div");
    card.tabIndex = 0;
    card.className = "composition-clip-card";
    card.dataset.clipId = clip.id;
    card.dataset.role = beat?.role || "development";
    card.classList.toggle("is-selected", clip.id === state.compositionSelectedClipId);
    card.setAttribute("role", "option");
    card.setAttribute("aria-selected", clip.id === state.compositionSelectedClipId ? "true" : "false");

    const rail = document.createElement("span");
    rail.className = "composition-clip-rail";
    const body = document.createElement("span");
    body.className = "composition-clip-body";
    const meta = document.createElement("span");
    meta.className = "composition-clip-meta";
    const role = document.createElement("span");
    role.className = "composition-clip-role";
    role.textContent = `${index + 1}. ${roleLabels[beat?.role] || beat?.role || "SCENE"}`;
    const duration = document.createElement("span");
    duration.className = "composition-clip-duration";
    duration.textContent = `${compositionClipDuration(clip).toFixed(1)}秒`;
    meta.append(role, duration);
    const textValue = document.createElement("span");
    textValue.className = "composition-clip-text";
    textValue.textContent = compositionClipSummary(clip);
    const actions = document.createElement("span");
    actions.className = "composition-clip-actions";
    for (const [action, label] of [["up", "↑"], ["down", "↓"], ["delete", "外す"]]) {
      const control = document.createElement("button");
      control.type = "button";
      control.dataset.action = action;
      control.textContent = label;
      control.addEventListener("click", (event) => {
        event.stopPropagation();
        if (action === "delete") deleteCompositionClip(clip.id);
        else moveCompositionClip(clip.id, action === "up" ? -1 : 1);
      });
      actions.append(control);
    }
    body.append(meta, textValue, actions);
    card.append(rail, body);
    card.addEventListener("click", () => selectCompositionClip(clip.id, { seek: true }));
    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectCompositionClip(clip.id, { seek: true });
    });
    elements.compositionClipList.append(card);
  }
}

function selectCompositionClip(clipId, { seek = false } = {}) {
  if (!compositionTimelineItems().some((item) => item.id === clipId)) return;
  state.compositionSelectedClipId = clipId;
  renderCompositionClipList();
  renderCompositionInspector();
  const clip = selectedCompositionClip();
  const layout = compositionLayoutForClip(clipId);
  if (layout === "person") state.compositionRegion = "person";
  if (layout === "content" || layout === "split") state.compositionRegion = "content";
  renderCompositionCropRect();
  if (seek && clip?.type === "source_clip") {
    const sourceTime = Math.max(0, compositionPtsSeconds(clip.video_in_pts));
    if (Number.isFinite(sourceTime)) elements.compositionSourceVideo.currentTime = sourceTime;
    if (state.compositionPreviewMode === "live") {
      const outputStart = compositionLiveOutputStartForClip(clip.id);
      if (Number.isFinite(outputStart)) setCompositionLiveOutputTime(outputStart);
    } else {
      const segment = (state.composition?.compiled?.video_segments || []).find(
        (value) => value.timeline_item_id === clip.id
      );
      const fps =
        Number(state.composition?.compiled?.output?.fps_num || 30) /
        Number(state.composition?.compiled?.output?.fps_den || 1);
      if (segment && Number.isFinite(fps) && fps > 0) {
        elements.compositionPreviewVideo.currentTime = Number(segment.output_start_frame) / fps;
      }
    }
  }
}

function moveCompositionClip(clipId, direction) {
  const items = compositionTimelineItems();
  const index = items.findIndex((item) => item.id === clipId);
  const next = index + direction;
  if (index < 0 || next < 0 || next >= items.length) return;
  if (items[index].story_beat_id !== items[next].story_beat_id) {
    showStatus("意味の区切りをまたぐ移動は、まずカットの役割を変更してから行います。", "error");
    return;
  }
  const beat = compositionBeatForClip(items[index]);
  if (beat?.source_order_lock) {
    showStatus("元動画の順序を守る区間なので、この2カットは入れ替えられません。", "error");
    return;
  }
  [items[index], items[next]] = [items[next], items[index]];
  updateCompositionBeatItems();
  rebuildCompositionJoins();
  state.compositionPreviewMode = "live";
  state.compositionSelectedRenderId = "";
  renderCompositionWorkspace();
  selectCompositionClip(clipId, { seek: true });
}

function deleteCompositionClip(clipId) {
  const items = compositionTimelineItems();
  if (items.length <= 1) {
    showStatus("最後の1カットは外せません。", "error");
    return;
  }
  const index = items.findIndex((item) => item.id === clipId);
  if (index < 0) return;
  state.compositionPlan.timeline_items = items.filter((item) => item.id !== clipId);
  state.compositionPlan.presentation_events = state.compositionPlan.presentation_events.filter(
    (event) => event.timeline_item_id !== clipId
  );
  state.compositionPlan.speech_captions = state.compositionPlan.speech_captions.filter(
    (caption) => caption.timeline_item_id !== clipId
  );
  state.compositionPlan.editorial_overlays = state.compositionPlan.editorial_overlays.filter(
    (overlay) => overlay.timeline_item_id !== clipId
  );
  updateCompositionBeatItems();
  rebuildCompositionJoins();
  const remaining = compositionTimelineItems();
  state.compositionSelectedClipId = remaining[Math.min(index, remaining.length - 1)].id;
  state.compositionPreviewMode = "live";
  state.compositionSelectedRenderId = "";
  renderCompositionWorkspace();
  selectCompositionClip(state.compositionSelectedClipId, { seek: true });
  showStatus("カットを外しました。保存前なら「変更を破棄」で戻せます。", "success");
}

function setCompositionClipLayout(layout) {
  const clip = selectedCompositionClip();
  if (!clip || clip.type !== "source_clip") return;
  const existing = (state.compositionPlan.presentation_events || []).filter(
    (event) => event.timeline_item_id === clip.id
  );
  const id = existing[0]?.id || `ui-layout-${clip.id}`.slice(0, 80);
  state.compositionPlan.presentation_events = state.compositionPlan.presentation_events.filter(
    (event) => event.timeline_item_id !== clip.id
  );
  state.compositionPlan.presentation_events.push({
    id,
    timeline_item_id: clip.id,
    source_in_pts: clip.video_in_pts,
    source_out_pts: clip.video_out_pts,
    layout,
  });
  if (layout === "person") state.compositionRegion = "person";
  if (layout === "content" || layout === "split") state.compositionRegion = "content";
  renderCompositionInspector();
  renderCompositionCropRect();
  compositionDraftChanged({ seekSelected: true });
}

function trimCompositionClip(field, deltaSeconds) {
  const clip = selectedCompositionClip();
  if (!clip || clip.type !== "source_clip") return;
  const oldIn = Number(clip.video_in_pts);
  const oldOut = Number(clip.video_out_pts);
  const ptsDelta = Math.round(Number(deltaSeconds) / compositionTimeBase());
  let newIn = field === "start" ? oldIn + ptsDelta : oldIn;
  let newOut = field === "end" ? oldOut + ptsDelta : oldOut;
  const sourceStart = Number(state.composition.source.video_start_pts || 0);
  const sourceEnd = sourceStart + Number(state.composition.source.video_duration_ts || 0);
  newIn = Math.max(sourceStart, newIn);
  newOut = Math.min(sourceEnd, newOut);
  const captions = compositionCaptionsForClip(clip.id);
  const earliestCaption = captions.length
    ? Math.min(...captions.map((caption) => Number(caption.source_in_pts)))
    : Number.POSITIVE_INFINITY;
  const latestCaption = captions.length
    ? Math.max(...captions.map((caption) => Number(caption.source_out_pts)))
    : Number.NEGATIVE_INFINITY;
  const fps = compositionFps();
  const minPts = Math.max(1, Math.ceil((3 / fps) / compositionTimeBase()));
  const overlayFrames = Math.max(
    0,
    ...(state.compositionPlan.editorial_overlays || [])
      .filter((overlay) => overlay.timeline_item_id === clip.id)
      .map((overlay) => Number(overlay.local_out_frame || 0))
  );
  const durationFrames = Math.floor(
    (newOut - newIn) * compositionTimeBase() * fps + 0.5
  );
  if (
    newOut - newIn < minPts ||
    newIn > earliestCaption ||
    newOut < latestCaption ||
    durationFrames < overlayFrames
  ) {
    elements.compositionTrimError.textContent =
      "字幕または画面テキストが範囲外になります。先にその要素を直してください。";
    elements.compositionTrimError.hidden = false;
    return;
  }
  elements.compositionTrimError.hidden = true;
  const sampleRate = Number(state.composition.source.audio_sample_rate || 48000);
  clip.video_in_pts = newIn;
  clip.video_out_pts = newOut;
  clip.audio_in_sample += Math.round((newIn - oldIn) * compositionTimeBase() * sampleRate);
  clip.audio_out_sample += Math.round((newOut - oldOut) * compositionTimeBase() * sampleRate);
  const nextPresentationEvents = [];
  for (const event of state.compositionPlan.presentation_events || []) {
    if (event.timeline_item_id !== clip.id) {
      nextPresentationEvents.push(event);
      continue;
    }
    const eventIn = Number(event.source_in_pts);
    const eventOut = Number(event.source_out_pts);
    const clippedIn = eventIn === oldIn ? newIn : Math.max(newIn, eventIn);
    const clippedOut = eventOut === oldOut ? newOut : Math.min(newOut, eventOut);
    if (clippedOut <= clippedIn) continue;
    nextPresentationEvents.push({
      ...event,
      source_in_pts: clippedIn,
      source_out_pts: clippedOut,
    });
  }
  state.compositionPlan.presentation_events = nextPresentationEvents;
  state.compositionPreviewMode = "live";
  state.compositionSelectedRenderId = "";
  renderCompositionWorkspace();
  selectCompositionClip(clip.id, { seek: true });
}

function renderCompositionInspector() {
  const clip = selectedCompositionClip();
  elements.compositionInspectorEmpty.hidden = Boolean(clip);
  elements.compositionInspector.hidden = !clip;
  if (!clip) return;
  const layout = compositionLayoutForClip(clip.id);
  for (const button of elements.compositionInspector.querySelectorAll(
    "[data-composition-layout]"
  )) {
    button.classList.toggle("is-active", button.dataset.compositionLayout === layout);
    button.disabled = state.compositionBusy || clip.type !== "source_clip";
  }
  if (clip.type === "source_clip") {
    elements.compositionClipTiming.textContent =
      `${formatTime(compositionPtsSeconds(clip.video_in_pts))} → ${formatTime(compositionPtsSeconds(clip.video_out_pts))}`;
  } else {
    elements.compositionClipTiming.textContent = `${compositionClipDuration(clip).toFixed(1)}秒`;
  }
  const captions = compositionCaptionsForClip(clip.id);
  elements.compositionCaptionCount.textContent = `${captions.length}件`;
  elements.compositionCaptionAddButton.disabled =
    state.compositionBusy || clip.type !== "source_clip";
  elements.compositionCaptionList.replaceChildren();
  for (const caption of captions) {
    elements.compositionCaptionList.append(createCompositionCaptionEditor(caption));
  }
  elements.compositionInspectorNote.textContent =
    layout === "mixed"
      ? "このカット内で複数レイアウトを使っています。ボタンを押すと1つへ統一します。"
      : "このカットを外すと、紐づく字幕と画面テキストも一緒に外れます。";
  updateCompositionDirtyState();
}

function compositionRegionRect() {
  const raw = state.compositionPlan?.source_regions?.[state.compositionRegion];
  return Array.isArray(raw) && raw.length === 4 ? raw : null;
}

function renderCompositionCropRect() {
  const rect = compositionRegionRect();
  if (!rect) {
    elements.compositionCropRect.hidden = true;
    return;
  }
  elements.compositionCropRect.hidden = false;
  elements.compositionCropRect.style.left = `${rect[0] / 10000}%`;
  elements.compositionCropRect.style.top = `${rect[1] / 10000}%`;
  elements.compositionCropRect.style.width = `${rect[2] / 10000}%`;
  elements.compositionCropRect.style.height = `${rect[3] / 10000}%`;
  const content = state.compositionRegion === "content";
  elements.compositionCropLabel.textContent = content ? "ゲーム重要範囲" : "顔の範囲";
  elements.compositionCropStatus.textContent = content
    ? "敵HPなど、見せたいUIが枠内に入るよう調整します。"
    : "表情と口元が枠内に入るよう調整します。";
  for (const button of document.querySelectorAll("[data-composition-region]")) {
    button.classList.toggle(
      "is-active",
      button.dataset.compositionRegion === state.compositionRegion
    );
  }
  updateCompositionDirtyState();
}

function updateCompositionRegionRect(rect, { preserveSize = false } = {}) {
  const normalized = [
    Math.round(Math.max(0, Math.min(999999, rect[0]))),
    Math.round(Math.max(0, Math.min(999999, rect[1]))),
    Math.round(Math.max(30000, Math.min(1000000, rect[2]))),
    Math.round(Math.max(30000, Math.min(1000000, rect[3]))),
  ];
  if (preserveSize) {
    normalized[0] = Math.min(normalized[0], 1000000 - normalized[2]);
    normalized[1] = Math.min(normalized[1], 1000000 - normalized[3]);
  } else {
    normalized[2] = Math.min(normalized[2], 1000000 - normalized[0]);
    normalized[3] = Math.min(normalized[3], 1000000 - normalized[1]);
  }
  state.compositionPlan.source_regions[state.compositionRegion] = normalized;
  renderCompositionCropRect();
  compositionDraftChanged();
}

function startCompositionCropDrag(event) {
  if (state.compositionBusy || event.button !== 0) return;
  const rect = compositionRegionRect();
  if (!rect) return;
  state.compositionCropPointer = {
    id: event.pointerId,
    x: event.clientX,
    y: event.clientY,
    rect: rect.slice(),
    resize: event.target.classList.contains("composition-crop-handle"),
  };
  elements.compositionCropRect.setPointerCapture(event.pointerId);
  event.preventDefault();
}

function moveCompositionCrop(event) {
  const pointer = state.compositionCropPointer;
  if (!pointer || pointer.id !== event.pointerId) return;
  const stage = elements.compositionSourceStage.getBoundingClientRect();
  if (!stage.width || !stage.height) return;
  const dx = ((event.clientX - pointer.x) / stage.width) * 1000000;
  const dy = ((event.clientY - pointer.y) / stage.height) * 1000000;
  const next = pointer.rect.slice();
  if (pointer.resize) {
    next[2] += dx;
    next[3] += dy;
  } else {
    next[0] += dx;
    next[1] += dy;
  }
  updateCompositionRegionRect(next, { preserveSize: !pointer.resize });
}

function endCompositionCrop(event) {
  if (state.compositionCropPointer?.id !== event.pointerId) return;
  state.compositionCropPointer = null;
  updateCompositionDirtyState();
}

function placeCompositionKeepVisiblePoint(event) {
  if (!state.compositionPinArmed) return;
  if (event.target.closest("button") || event.target === elements.compositionCropRect) return;
  const stage = elements.compositionSourceStage.getBoundingClientRect();
  const x = Math.max(0, Math.min(1000000, ((event.clientX - stage.left) / stage.width) * 1000000));
  const y = Math.max(0, Math.min(1000000, ((event.clientY - stage.top) / stage.height) * 1000000));
  const rect = compositionRegionRect();
  if (!rect) return;
  const marginX = rect[2] * 0.16;
  const marginY = rect[3] * 0.16;
  const next = rect.slice();
  if (x < rect[0] + marginX) next[0] = x - marginX;
  if (x > rect[0] + rect[2] - marginX) next[0] = x - rect[2] + marginX;
  if (y < rect[1] + marginY) next[1] = y - marginY;
  if (y > rect[1] + rect[3] - marginY) next[1] = y - rect[3] + marginY;
  updateCompositionRegionRect(next, { preserveSize: true });
  elements.compositionPinMarker.hidden = false;
  elements.compositionPinMarker.style.left = `${x / 10000}%`;
  elements.compositionPinMarker.style.top = `${y / 10000}%`;
  state.compositionPinArmed = false;
  elements.compositionKeepVisibleButton.classList.remove("is-armed");
  elements.compositionKeepVisibleButton.textContent = "＋ 見切れ禁止点";
  elements.compositionCropStatus.textContent = "指定点が余白を持って枠内へ入るよう移動しました。";
  updateCompositionDirtyState();
  event.preventDefault();
}

function discardCompositionChanges() {
  if (!state.originalCompositionPlan) return;
  pauseCompositionLivePreview();
  state.compositionPlan = cloneJson(state.originalCompositionPlan);
  state.compositionSelectedClipId = compositionTimelineItems().some(
    (item) => item.id === state.compositionSelectedClipId
  )
    ? state.compositionSelectedClipId
    : compositionTimelineItems()[0]?.id || "";
  state.compositionPreviewMode = "live";
  state.compositionSelectedRenderId = "";
  renderCompositionWorkspace();
  selectCompositionClip(state.compositionSelectedClipId, { seek: true });
  showStatus("未保存の構成変更を破棄しました。", "success");
}

async function saveComposition() {
  if (state.compositionBusy || !compositionIsDirty()) return;
  pauseCompositionLivePreview();
  setCompositionBusy(true);
  const projectId = compositionProjectId();
  let savedRevision = null;
  try {
    showStatus("新しいRevisionを保存しています…", "info");
    const savePayload = await apiRequest(
      `/api/compositions/${encodeURIComponent(projectId)}/edits`,
      {
        method: "PUT",
        mutation: true,
        body: {
          base_revision: state.composition.edit.revision,
          plan: state.compositionPlan,
        },
      }
    );
    const saveResult = await waitForOperation(savePayload.status_url);
    savedRevision = Number(saveResult.revision);
    showStatus(`Revision ${savedRevision}を保存しました。続けてProxyを生成しています…`, "info");
    const renderPayload = await apiRequest(
      `/api/compositions/${encodeURIComponent(projectId)}/renders`,
      {
        method: "POST",
        mutation: true,
        body: { edit_revision: savedRevision, profile: "proxy" },
      }
    );
    const renderResult = await waitForOperation(renderPayload.status_url);
    await loadComposition(projectId, renderResult.render_id);
    showStatus(`Revision ${savedRevision}を保存し、Proxyへ反映しました。`, "success");
  } catch (error) {
    if (savedRevision !== null) {
      try {
        await loadComposition(projectId);
      } catch (_reloadError) {
        // The immutable revision is already safe even if refreshing the view also fails.
      }
      showStatus(
        `Revision ${savedRevision}は保存済みですが、Proxy更新に失敗しました。` +
          `「Proxyを更新」で再試行できます。${error.message}`,
        "error"
      );
    } else {
      showStatus(error.message, "error");
    }
  } finally {
    setCompositionBusy(false);
  }
}

async function renderCompositionProxy() {
  if (state.compositionBusy || compositionIsDirty() || !state.composition?.edit?.revision) return;
  setCompositionBusy(true);
  showStatus("現在のRevisionからproxyを生成しています…", "info");
  try {
    const projectId = compositionProjectId();
    const payload = await apiRequest(
      `/api/compositions/${encodeURIComponent(projectId)}/renders`,
      {
        method: "POST",
        mutation: true,
        body: { edit_revision: state.composition.edit.revision, profile: "proxy" },
      }
    );
    const result = await waitForOperation(payload.status_url);
    await loadComposition(projectId, result.render_id);
    showStatus("新しいproxyを生成しました。", "success");
  } catch (error) {
    showStatus(error.message, "error");
  } finally {
    setCompositionBusy(false);
  }
}

async function toggleVideoFullscreen() {
  try {
    if (document.fullscreenElement === elements.videoShell) {
      await document.exitFullscreen();
    } else if (elements.videoShell.requestFullscreen) {
      await elements.videoShell.requestFullscreen();
    }
  } catch (_error) {
    showStatus("このブラウザでは全画面表示を開始できませんでした。", "error");
  }
}

function seekVideoBy(delta) {
  const duration = Number(elements.previewVideo.duration);
  const current = Number(elements.previewVideo.currentTime);
  if (!Number.isFinite(duration) || !Number.isFinite(current)) return;
  const target = Math.min(duration, Math.max(0, Math.round((current + delta) * 1000) / 1000));
  elements.previewVideo.currentTime = target;
  paintLiveCaption(target);
  elements.previewVideo.focus();
}

elements.candidateModeButton.addEventListener("click", () => switchMode("candidate"));
elements.compositionModeButton.addEventListener("click", () => switchMode("composition"));
elements.candidateDropZone.addEventListener("click", () => {
  if (!state.candidateBusy) elements.candidateFileInput.click();
});
elements.candidateDropZone.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  if (!state.candidateBusy) elements.candidateFileInput.click();
});
for (const eventName of ["dragenter", "dragover"]) {
  elements.candidateDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!state.candidateBusy) elements.candidateDropZone.classList.add("is-dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.candidateDropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.candidateDropZone.classList.remove("is-dragging");
  });
}
elements.candidateDropZone.addEventListener("drop", (event) => {
  if (state.candidateBusy) return;
  const files = Array.from(event.dataTransfer?.files || []);
  if (files.length !== 1) {
    elements.candidateFormError.textContent = "動画は1本ずつ選択してください。";
    elements.candidateFormError.hidden = false;
    return;
  }
  selectCandidateFile(files[0]);
});
elements.candidateFileInput.addEventListener("change", () => {
  const file = elements.candidateFileInput.files?.[0];
  if (file) selectCandidateFile(file);
});
elements.candidateRightsCheckbox.addEventListener("change", updateCandidateStartState);
elements.candidateLocalProcessingCheckbox.addEventListener("change", updateCandidateStartState);
elements.candidateStartButton.addEventListener("click", startCandidateSearch);
elements.candidateCancelButton.addEventListener("click", cancelCandidateRun);
elements.candidateResumeButton.addEventListener("click", resumeCandidateRun);
elements.candidateResetButton.addEventListener("click", () => resetCandidateClientState());
elements.candidateHistoryOpenButton.addEventListener("click", () => openCandidateHistoryRun());
elements.candidateHistorySelect.addEventListener("change", () => {
  elements.candidateHistoryOpenButton.disabled = !elements.candidateHistorySelect.value;
});
for (const input of [elements.candidateRangeStart, elements.candidateRangeEnd]) {
  input.addEventListener("input", () => validateCandidateRange());
  input.addEventListener("blur", () => validateCandidateRange({ normalizeInputs: true }));
}
elements.candidateStartFromPlayhead.addEventListener("click", () => {
  setCandidateBoundaryFromPlayhead("start");
});
elements.candidateEndFromPlayhead.addEventListener("click", () => {
  setCandidateBoundaryFromPlayhead("end");
});
elements.candidateSeekStart.addEventListener("click", () => {
  if (validateCandidateRange()) seekCandidateSource(state.candidateRange.start);
});
elements.candidateSeekEnd.addEventListener("click", () => {
  if (validateCandidateRange()) seekCandidateSource(Math.max(0, state.candidateRange.end - 0.1));
});
elements.candidateAdoptButton.addEventListener("click", adoptCandidateRange);
for (const button of document.querySelectorAll("[data-candidate-seek]")) {
  button.addEventListener("click", () => {
    const delta = Number(button.dataset.candidateSeek);
    const current = Number(elements.candidatePreviewVideo.currentTime);
    if (Number.isFinite(delta) && Number.isFinite(current)) {
      seekCandidateSource(Math.round((current + delta) * 1000) / 1000);
    }
  });
}
elements.candidatePreviewVideo.addEventListener("loadedmetadata", () => {
  if (state.candidateRange) seekCandidateSource(state.candidateRange.start);
  validateCandidateRange();
});
elements.candidatePreviewVideo.addEventListener("timeupdate", () => {
  const current = Number(elements.candidatePreviewVideo.currentTime);
  elements.candidateSourceTime.textContent = Number.isFinite(current)
    ? formatTime(current)
    : "—";
  if (
    elements.candidateLoopCheckbox.checked &&
    state.candidateRange &&
    current >= state.candidateRange.end
  ) {
    elements.candidatePreviewVideo.currentTime = state.candidateRange.start;
  }
});
elements.candidatePreviewVideo.addEventListener("error", () => {
  elements.candidatePreviewLabel.textContent =
    "元動画をブラウザで再生できませんでした。候補結果は保持されています。";
});

elements.compositionProjectSelect.addEventListener("change", () => {
  if (compositionBlockIfDirty()) return;
  loadComposition(elements.compositionProjectSelect.value);
});
elements.compositionReloadButton.addEventListener("click", () => {
  if (compositionBlockIfDirty()) return;
  loadComposition(elements.compositionProjectSelect.value);
});
elements.compositionRenderSelect.addEventListener("change", () => {
  const selectedValue = elements.compositionRenderSelect.value;
  if (selectedValue === "live") {
    showCompositionLivePreview({ preserveTime: true });
    return;
  }
  state.compositionPreviewMode = "render";
  state.compositionSelectedRenderId = selectedValue;
  const render = (state.composition?.renders || []).find(
    (item) => item.render_id === state.compositionSelectedRenderId
  );
  updateCompositionPreview(render);
});
elements.compositionLivePlayButton.addEventListener("click", () => {
  if (state.compositionLivePlaying) pauseCompositionLivePreview();
  else playCompositionLivePreview();
});
elements.compositionLiveCanvas.addEventListener("click", () => {
  if (state.compositionLivePlaying) pauseCompositionLivePreview();
  else playCompositionLivePreview();
});
elements.compositionLiveSeek.addEventListener("input", () => {
  const keepPlaying = state.compositionLivePlaying;
  setCompositionLiveOutputTime(Number(elements.compositionLiveSeek.value), { keepPlaying });
});
elements.compositionLiveSource.addEventListener("loadedmetadata", () => {
  setCompositionLiveOutputTime(state.compositionLiveOutputTime, {
    keepPlaying: state.compositionLivePlaying,
  });
});
elements.compositionLiveSource.addEventListener("seeked", drawCompositionLivePreview);
elements.compositionLiveSource.addEventListener("loadeddata", drawCompositionLivePreview);
elements.compositionLiveSource.addEventListener("error", () => {
  pauseCompositionLivePreview();
  showStatus("元動画をライブプレビューへ読み込めませんでした。", "error");
});
elements.compositionSourceVideo.addEventListener("play", pauseCompositionLivePreview);
elements.compositionPreviewVideo.addEventListener("play", pauseCompositionLivePreview);
elements.compositionSaveButton.addEventListener("click", saveComposition);
elements.compositionDiscardButton.addEventListener("click", discardCompositionChanges);
elements.compositionRenderButton.addEventListener("click", renderCompositionProxy);
elements.compositionCaptionAddButton.addEventListener("click", () => addCompositionCaption());
for (const button of document.querySelectorAll("[data-composition-section]")) {
  button.addEventListener("click", () =>
    switchCompositionSection(button.dataset.compositionSection)
  );
}
for (const button of document.querySelectorAll("[data-composition-layout]")) {
  button.addEventListener("click", () => setCompositionClipLayout(button.dataset.compositionLayout));
}
for (const button of document.querySelectorAll("[data-composition-trim]")) {
  button.addEventListener("click", () => {
    const [field, delta] = button.dataset.compositionTrim.split(":");
    trimCompositionClip(field, Number(delta));
  });
}
for (const button of document.querySelectorAll("[data-composition-region]")) {
  button.addEventListener("click", () => {
    state.compositionRegion = button.dataset.compositionRegion;
    elements.compositionPinMarker.hidden = true;
    renderCompositionCropRect();
  });
}
elements.compositionCropRect.addEventListener("pointerdown", startCompositionCropDrag);
elements.compositionCropRect.addEventListener("pointermove", moveCompositionCrop);
elements.compositionCropRect.addEventListener("pointerup", endCompositionCrop);
elements.compositionCropRect.addEventListener("pointercancel", endCompositionCrop);
elements.compositionKeepVisibleButton.addEventListener("click", () => {
  state.compositionPinArmed = !state.compositionPinArmed;
  elements.compositionKeepVisibleButton.classList.toggle("is-armed", state.compositionPinArmed);
  elements.compositionKeepVisibleButton.textContent = state.compositionPinArmed
    ? "映像上をクリック"
    : "＋ 見切れ禁止点";
  elements.compositionCropStatus.textContent = state.compositionPinArmed
    ? "敵HPなど、絶対に残したい場所を映像上でクリックしてください。"
    : "見切れ禁止点の指定を解除しました。";
});
elements.compositionSourceStage.addEventListener("pointerdown", placeCompositionKeepVisiblePoint);
window.addEventListener("beforeunload", (event) => {
  if (!compositionIsDirty() && !state.candidateUpload) return;
  event.preventDefault();
  event.returnValue = "";
});

(async () => {
  try {
    await establishSession();
    setConnection("localhost 接続済み", "ok");
    elements.startupPanel.hidden = true;
    elements.workspace.hidden = false;
    switchMode("candidate", { force: true });
    await loadCandidateHistory();
    await restoreCandidateRun();
    await loadCompositionProjects();
  } catch (error) {
    setConnection("接続できません", "error");
    elements.startupMessage.textContent =
      error.status === 401
        ? "起動時に表示された新しいURLから開き直してください。"
        : error.message;
  }
})();
