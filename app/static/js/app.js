/* ==========================================================
   FreeVidGrab — Frontend Logic
   ========================================================== */

const $ = (sel) => document.querySelector(sel);

const urlInput     = $("#urlInput");
const parseBtn     = $("#parseBtn");
const errorMsg     = $("#errorMsg");
const resultSection   = $("#resultSection");
const resultThumb     = $("#resultThumb");
const resultDuration  = $("#resultDuration");
const resultTitle     = $("#resultTitle");
const resultUploader  = $("#resultUploader");
const formatList      = $("#formatList");
const downloadBtn     = $("#downloadBtn");
const progressSection = $("#progressSection");
const progressIcon    = $("#progressIcon");
const progressLabel   = $("#progressLabel");
const progressDetail  = $("#progressDetail");
const progressBar     = $("#progressBar");
const progressPercent = $("#progressPercent");
const saveFileLink    = $("#saveFileLink");

let selectedFormat = null;
let currentVideoUrl = "";
let _parseTimer = null;
let _parsing = false;

// -----------------------------------------------------------
// Helpers
// -----------------------------------------------------------

function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.classList.remove("hidden");
}
function hideError() {
    errorMsg.classList.add("hidden");
}

function formatDuration(sec) {
    if (!sec) return "";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatFileSize(bytes) {
    if (!bytes) return "";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function setLoading(loading) {
    if (loading) {
        parseBtn.disabled = true;
        parseBtn.innerHTML = '<span class="spinner"></span>';
    } else {
        parseBtn.disabled = false;
        parseBtn.textContent = "解析视频";
    }
}

// -----------------------------------------------------------
// Parse
// -----------------------------------------------------------

async function parseVideo() {
    if (_parsing) return;
    const url = urlInput.value.trim();
    if (!url) { showError("请粘贴视频链接"); return; }
    hideError();
    resultSection.classList.add("hidden");
    progressSection.classList.add("hidden");
    setLoading(true);
    _parsing = true;

    try {
        const res = await fetch("/api/parse", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        const data = await res.json();
        if (!res.ok) {
            showError(data.detail || "解析失败，请检查链接");
            return;
        }

        hideError();
        currentVideoUrl = data.webpage_url || url;
        renderResult(data);
    } catch (e) {
        showError("网络错误，请稍后重试");
    } finally {
        setLoading(false);
        _parsing = false;
    }
}

function renderResult(info) {
    hideError();
    resultThumb.src = info.thumbnail || "";
    resultThumb.alt = info.title;
    resultDuration.textContent = formatDuration(info.duration);
    resultTitle.textContent = info.title;
    resultUploader.textContent = info.uploader ? `上传者: ${info.uploader}` : "";

    formatList.innerHTML = "";
    selectedFormat = null;
    downloadBtn.disabled = true;
    downloadBtn.textContent = "选择清晰度后下载";

    const formats = info.formats || [];
    if (formats.length === 0) {
        formatList.innerHTML = '<p class="col-span-full text-slate-400 text-sm">未检测到可下载的格式</p>';
    }

    formats.forEach((f, idx) => {
        const pill = document.createElement("div");
        pill.className = "format-pill";
        pill.dataset.formatId = f.format_id;
        pill.innerHTML = `
            <span class="label">${f.label}</span>
            <span class="meta">${f.ext.toUpperCase()}${f.filesize ? " · " + formatFileSize(f.filesize) : ""}</span>
        `;
        pill.addEventListener("click", () => selectFormat(pill, f));
        formatList.appendChild(pill);

        if (idx === 0) selectFormat(pill, f);
    });

    resultSection.classList.remove("hidden");
    resultSection.classList.add("fade-in-up");
    resultSection.scrollIntoView({ behavior: "smooth", block: "center" });
}

function selectFormat(pill, f) {
    document.querySelectorAll(".format-pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    selectedFormat = f;
    downloadBtn.disabled = false;
    downloadBtn.textContent = `下载 ${f.label} (${f.ext.toUpperCase()})`;
}

// -----------------------------------------------------------
// Download + SSE progress
// -----------------------------------------------------------

async function startDownload() {
    if (!currentVideoUrl || !selectedFormat) return;
    downloadBtn.disabled = true;
    hideError();

    try {
        const res = await fetch("/api/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: currentVideoUrl,
                format_id: selectedFormat.format_id,
                audio_id: selectedFormat.best_audio_id || null,
            }),
        });
        const data = await res.json();
        if (!res.ok) {
            showError(data.detail || "下载请求失败");
            downloadBtn.disabled = false;
            return;
        }

        showProgress();
        listenProgress(data.task_id);
    } catch (e) {
        showError("网络错误，请稍后重试");
        downloadBtn.disabled = false;
    }
}

function showProgress() {
    progressSection.classList.remove("hidden");
    progressSection.classList.add("fade-in-up");
    progressIcon.textContent = "⏳";
    progressLabel.textContent = "正在下载...";
    progressDetail.textContent = "";
    progressBar.style.width = "0%";
    progressPercent.textContent = "0%";
    saveFileLink.classList.add("hidden");
    progressSection.scrollIntoView({ behavior: "smooth", block: "center" });
}

function listenProgress(taskId) {
    const evtSource = new EventSource(`/api/progress/${taskId}`);

    evtSource.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.status === "heartbeat") return;

        if (data.status === "downloading") {
            const pct = Math.min(data.percent || 0, 100);
            progressBar.style.width = pct + "%";
            progressPercent.textContent = pct.toFixed(1) + "%";
            progressLabel.textContent = "正在下载...";
            const parts = [];
            if (data.speed) parts.push(data.speed);
            if (data.eta) parts.push("剩余 " + data.eta);
            progressDetail.textContent = parts.join("  ·  ");
        }

        if (data.status === "merging") {
            progressBar.style.width = "100%";
            progressPercent.textContent = "100%";
            progressLabel.textContent = "正在合并音视频...";
            progressDetail.textContent = "即将完成";
        }

        if (data.status === "done") {
            evtSource.close();
            progressIcon.textContent = "✅";
            progressLabel.textContent = "下载完成!";
            progressDetail.textContent = "";
            progressBar.style.width = "100%";
            progressPercent.textContent = "100%";

            saveFileLink.href = `/api/file/${taskId}`;
            saveFileLink.classList.remove("hidden");
            downloadBtn.disabled = false;
        }

        if (data.status === "error") {
            evtSource.close();
            progressIcon.textContent = "❌";
            progressLabel.textContent = "下载失败";
            progressDetail.textContent = data.error || "未知错误";
            downloadBtn.disabled = false;
        }
    };

    evtSource.onerror = () => {
        evtSource.close();
        progressIcon.textContent = "❌";
        progressLabel.textContent = "连接中断";
        progressDetail.textContent = "请重试";
        downloadBtn.disabled = false;
    };
}

// -----------------------------------------------------------
// Event bindings
// -----------------------------------------------------------

parseBtn.addEventListener("click", parseVideo);
downloadBtn.addEventListener("click", startDownload);

urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") parseVideo();
});

urlInput.addEventListener("paste", () => {
    clearTimeout(_parseTimer);
    _parseTimer = setTimeout(parseVideo, 300);
});
