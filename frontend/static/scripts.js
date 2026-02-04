/**
 * Paper Reader - Frontend JavaScript
 * Handles WebSocket communication, file upload, and UI interactions
 */

// ============================================
// Global State
// ============================================

const state = {
    uploadId: null,
    sessionId: null,
    reportId: null,
    websocket: null,
    reports: { english: '', chinese: '' },
    specialistReports: {},
    currentLang: 'en'
};

// Markdown converter
const converter = new showdown.Converter({
    tables: true,
    strikethrough: true,
    tasklists: true,
    ghCodeBlocks: true,
    smoothLivePreview: true,
    simpleLineBreaks: true
});

// ============================================
// DOM Elements
// ============================================

const elements = {
    // Landing
    landingSection: document.getElementById('landingSection'),
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    uploadProgress: document.getElementById('uploadProgress'),
    uploadFileName: document.getElementById('uploadFileName'),
    uploadPercent: document.getElementById('uploadPercent'),
    uploadProgressBar: document.getElementById('uploadProgressBar'),
    settingsPanel: document.getElementById('settingsPanel'),
    startAnalysisBtn: document.getElementById('startAnalysisBtn'),

    // Settings
    analysisMode: document.getElementById('analysisMode'),
    llmProvider: document.getElementById('llmProvider'),
    llmModel: document.getElementById('llmModel'),

    // Analysis
    analysisSection: document.getElementById('analysisSection'),
    progressSteps: document.getElementById('progressSteps'),

    // Report
    reportPanel: document.getElementById('reportPanel'),
    reportTitle: document.getElementById('reportTitle'),
    reportContent: document.getElementById('reportContent'),

    // Chat
    chatSection: document.getElementById('chatSection'),
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    sendChatBtn: document.getElementById('sendChatBtn'),
    toggleChat: document.getElementById('toggleChat'),
    openChatBtn: document.getElementById('openChatBtn'),

    // History
    historyBtn: document.getElementById('historyBtn'),
    historySidebar: document.getElementById('historySidebar'),
    closeHistory: document.getElementById('closeHistory'),
    historyList: document.getElementById('historyList'),
    historySearch: document.getElementById('historySearch'),

    // Utils
    toast: document.getElementById('toast'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText')
};

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initTabs();
    initExport();
    initChat();
    initHistory();
    initSpecialistReports();
    loadHistory();
});

// ============================================
// File Upload
// ============================================

function initUpload() {
    const { uploadArea, fileInput } = elements;

    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());

    // File selected
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type === 'application/pdf') {
                handleFileUpload(file);
            } else {
                showToast('请上传 PDF 文件', 'error');
            }
        }
    });

    // Start analysis button
    elements.startAnalysisBtn.addEventListener('click', startAnalysis);
}

async function handleFileUpload(file) {
    const { uploadProgress, uploadFileName, uploadPercent, uploadProgressBar, settingsPanel, uploadArea } = elements;

    // Show progress
    uploadProgress.classList.remove('hidden');
    uploadFileName.textContent = file.name;
    uploadArea.style.display = 'none';

    // Create form data
    const formData = new FormData();
    formData.append('file', file);

    try {
        // Upload with progress
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadPercent.textContent = `${percent}%`;
                uploadProgressBar.style.width = `${percent}%`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                state.uploadId = response.upload_id;

                // Show settings panel
                settingsPanel.classList.remove('hidden');
                showToast('文件上传成功！', 'success');
            } else {
                throw new Error('Upload failed');
            }
        });

        xhr.addEventListener('error', () => {
            showToast('上传失败，请重试', 'error');
            uploadArea.style.display = 'block';
            uploadProgress.classList.add('hidden');
        });

        xhr.open('POST', '/api/upload');
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        showToast('上传失败: ' + error.message, 'error');
    }
}

// ============================================
// WebSocket & Analysis
// ============================================

function startAnalysis() {
    const { landingSection, analysisSection } = elements;

    // Generate session ID
    state.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Switch to analysis view
    landingSection.classList.add('hidden');
    analysisSection.classList.remove('hidden');

    // Connect WebSocket
    connectWebSocket();
}

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${state.sessionId}`;

    state.websocket = new WebSocket(wsUrl);

    state.websocket.onopen = () => {
        console.log('WebSocket connected');

        // Send analysis request
        state.websocket.send(JSON.stringify({
            type: 'analyze',
            upload_id: state.uploadId,
            mode: elements.analysisMode.value,
            provider: elements.llmProvider.value,
            model: elements.llmModel.value,
            verbose: false
        }));
    };

    state.websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    state.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        showToast('连接错误', 'error');
    };

    state.websocket.onclose = () => {
        console.log('WebSocket closed');
    };
}

function handleWebSocketMessage(data) {
    console.log('WS message:', data);

    switch (data.type) {
        case 'progress':
            updateProgress(data);
            break;
        case 'complete':
            handleAnalysisComplete(data);
            break;
        case 'error':
            handleAnalysisError(data);
            break;
    }
}

function updateProgress(data) {
    const { phase, agent, status, message } = data;

    // Find the matching step element
    let stepElement;

    if (phase === 'parsing') {
        stepElement = document.querySelector('.progress-step[data-phase="parsing"]');
    } else {
        stepElement = document.querySelector(`.progress-step[data-agent="${agent}"]`);
    }

    if (!stepElement) return;

    // Update step status
    const statusElement = stepElement.querySelector('.step-status');
    statusElement.textContent = message;

    // Update step classes
    stepElement.classList.remove('active', 'completed', 'error');

    switch (status) {
        case 'started':
        case 'in_progress':
            stepElement.classList.add('active');
            break;
        case 'completed':
            stepElement.classList.add('completed');
            break;
        case 'error':
            stepElement.classList.add('error');
            break;
    }
}

function handleAnalysisComplete(data) {
    const { reports, metadata } = data;

    state.reports = reports;
    state.reportId = metadata.report_id;

    // Mark all progress steps as completed (since orchestrator doesn't send individual updates)
    const allSteps = document.querySelectorAll('.progress-step');
    allSteps.forEach(step => {
        step.classList.remove('active');
        step.classList.add('completed');
        const statusEl = step.querySelector('.step-status');
        if (statusEl) {
            statusEl.textContent = '已完成';
        }
    });

    // Show report panel
    elements.reportPanel.classList.remove('hidden');

    // Update title
    if (metadata.title) {
        elements.reportTitle.innerHTML = `<i class="fas fa-file-alt"></i> ${metadata.title}`;
    }

    // Render reports
    renderReport('en', reports.english);
    renderReport('zh', reports.chinese);

    // Render specialist reports if available
    console.log('[handleAnalysisComplete] metadata:', metadata);
    console.log('[handleAnalysisComplete] specialist_reports:', metadata.specialist_reports);
    if (metadata.specialist_reports) {
        state.specialistReports = metadata.specialist_reports;
        renderSpecialistReports(metadata.specialist_reports);
    }

    // Show chat section
    elements.chatSection.classList.remove('hidden');

    showToast('分析完成！', 'success');
}

function handleAnalysisError(data) {
    showToast(`分析错误: ${data.error}`, 'error');
}

// ============================================
// Report Display
// ============================================

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.dataset.lang;

            // Update active tab
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Show corresponding content
            document.querySelectorAll('.report-lang').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelector(`.report-lang[data-lang="${lang}"]`).classList.add('active');

            state.currentLang = lang;
        });
    });
}

function renderReport(lang, markdown) {
    const container = document.querySelector(`.report-lang[data-lang="${lang}"]`);
    if (!container || !markdown) return;

    console.log(`[renderReport] lang=${lang}, uploadId=${state.uploadId}`);

    // Debug: show what image references exist in the markdown
    const imageMatches = markdown.match(/!\[([^\]]*)\]\(([^)]+)\)/g);
    if (imageMatches) {
        console.log(`[renderReport] Found ${imageMatches.length} image references:`, imageMatches.slice(0, 3));
    } else {
        console.log('[renderReport] No image references found in markdown');
    }

    // Fix image paths: convert relative paths to absolute URLs
    // Pattern: ![alt](images/Figure_X.png) -> ![alt](/outputs/upload_id/images/Figure_X.png)
    if (state.uploadId) {
        const originalMarkdown = markdown;
        markdown = markdown.replace(
            /!\[([^\]]*)\]\(images\/([^)]+)\)/g,
            `![$1](/outputs/${state.uploadId}/images/$2)`
        );
        console.log(`[renderReport] Image paths converted: ${originalMarkdown !== markdown}`);
        if (originalMarkdown !== markdown) {
            console.log('[renderReport] Sample conversion:', markdown.match(/!\[.*?\]\(\/outputs.*?\)/)?.[0]);
        }
    } else {
        console.warn('[renderReport] No uploadId set, images will not load!');
    }

    // CRITICAL: Protect LaTeX from Markdown processor
    // Use HTML comments as placeholders - Showdown will preserve these
    const mathBlocks = [];
    let mathIndex = 0;

    // Protect display math: $$...$$
    markdown = markdown.replace(/\$\$[\s\S]*?\$\$/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Protect inline math: $...$
    markdown = markdown.replace(/\$[^\$\n]+?\$/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Convert markdown to HTML
    let html = converter.makeHtml(markdown);

    // Step 2: Restore LaTeX blocks from HTML comments
    html = html.replace(/<!--MATH(\d+)-->/g, (match, index) => {
        return mathBlocks[parseInt(index)] || match;
    });

    container.innerHTML = html;

    // Highlight code blocks
    container.querySelectorAll('pre code').forEach(block => {
        hljs.highlightElement(block);
    });

    // Render LaTeX math using KaTeX
    // Wait a bit for DOM to settle, then render
    setTimeout(() => {
        try {
            renderMathInElement(container, {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '$', right: '$', display: false },
                    { left: '\\[', right: '\\]', display: true },
                    { left: '\\(', right: '\\)', display: false }
                ],
                throwOnError: false,
                trust: true,  // Allow commands like \text, \color, etc.
                strict: false  // Be lenient with LaTeX grammar
            });
        } catch (error) {
            console.error('KaTeX rendering error:', error);
        }
    }, 100);
}


// ============================================
// Specialist Reports
// ============================================

function initSpecialistReports() {
    const specialistToggle = document.getElementById('specialistToggle');
    const specialistContent = document.getElementById('specialistContent');
    const specialistTabBtns = document.querySelectorAll('.specialist-tab-btn');

    // Toggle expand/collapse
    if (specialistToggle) {
        specialistToggle.addEventListener('click', () => {
            specialistToggle.classList.toggle('expanded');
            specialistContent.classList.toggle('expanded');
        });
    }

    // Tab switching
    specialistTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const specialist = btn.dataset.specialist;

            // Update active tab
            specialistTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Show corresponding content
            document.querySelectorAll('.specialist-report').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelector(`.specialist-report[data-specialist="${specialist}"]`).classList.add('active');
        });
    });
}

function renderSpecialistReports(specialistReports) {
    console.log('[renderSpecialistReports] called with:', specialistReports);
    if (!specialistReports || Object.keys(specialistReports).length === 0) {
        console.log('[renderSpecialistReports] No specialist reports, returning');
        return; // No specialist reports available
    }

    const section = document.getElementById('specialistReportsSection');
    const countBadge = section.querySelector('.specialist-count');

    // Count available reports
    const count = Object.keys(specialistReports).length;
    countBadge.textContent = `(${count})`;

    // Render each specialist report
    Object.entries(specialistReports).forEach(([key, markdown]) => {
        const container = document.querySelector(`.specialist-report[data-specialist="${key}"]`);
        if (!container || !markdown) return;

        // CRITICAL: Protect LaTeX from Markdown processor (same as main reports)
        const mathBlocks = [];
        let mathIndex = 0;

        // Protect display math: $$...$$
        markdown = markdown.replace(/\$\$[\s\S]*?\$\$/g, (match) => {
            mathBlocks.push(match);
            return `<!--MATH${mathIndex++}-->`;
        });

        // Protect inline math: $...$
        markdown = markdown.replace(/\$[^\$\n]+?\$/g, (match) => {
            mathBlocks.push(match);
            return `<!--MATH${mathIndex++}-->`;
        });

        // Convert markdown to HTML
        let html = converter.makeHtml(markdown);

        // Restore LaTeX blocks from HTML comments
        html = html.replace(/<!--MATH(\d+)-->/g, (match, index) => {
            return mathBlocks[parseInt(index)] || match;
        });

        container.innerHTML = html;

        // Highlight code blocks
        container.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });

        // Render LaTeX math
        setTimeout(() => {
            try {
                renderMathInElement(container, {
                    delimiters: [
                        { left: '$$', right: '$$', display: true },
                        { left: '$', right: '$', display: false },
                        { left: '\\[', right: '\\]', display: true },
                        { left: '\\(', right: '\\)', display: false }
                    ],
                    throwOnError: false,
                    trust: true,
                    strict: false
                });
            } catch (error) {
                console.error('KaTeX rendering error in specialist report:', error);
            }
        }, 100);
    });

    // Show the section
    section.classList.remove('hidden');
}


// ============================================
// Export Functions
// ============================================

function initExport() {
    const exportBtns = document.querySelectorAll('.export-btn[data-format]');

    exportBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const format = btn.dataset.format;
            exportReport(format);
        });
    });

    // Copy to clipboard
    document.getElementById('copyReport').addEventListener('click', copyReportToClipboard);

    // Download images
    document.getElementById('downloadImages').addEventListener('click', downloadImages);
}

async function exportReport(format) {
    if (!state.reportId) {
        showToast('没有可导出的报告', 'error');
        return;
    }

    const lang = state.currentLang;
    const url = `/api/reports/${state.reportId}/export/${format}?lang=${lang}`;

    try {
        showLoading('正在生成文件...');

        const response = await fetch(url);
        if (!response.ok) throw new Error('Export failed');

        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);

        // Get filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `report.${format}`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?(.+)"?/);
            if (match) filename = match[1];
        }

        // Trigger download
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        a.click();

        URL.revokeObjectURL(downloadUrl);
        hideLoading();
        showToast('下载成功！', 'success');

    } catch (error) {
        hideLoading();
        showToast('导出失败: ' + error.message, 'error');
    }
}

function copyReportToClipboard() {
    const content = state.currentLang === 'en' ? state.reports.english : state.reports.chinese;

    navigator.clipboard.writeText(content).then(() => {
        showToast('已复制到剪贴板', 'success');
    }).catch(err => {
        showToast('复制失败', 'error');
    });
}

async function downloadImages() {
    if (!state.uploadId) return;

    const url = `/api/uploads/${state.uploadId}/images`;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('No images available');

        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `images_${state.uploadId}.zip`;
        a.click();

        URL.revokeObjectURL(downloadUrl);
        showToast('图片下载成功！', 'success');

    } catch (error) {
        showToast('下载失败: ' + error.message, 'error');
    }
}

// ============================================
// Chat Functionality
// ============================================

function initChat() {
    elements.sendChatBtn.addEventListener('click', sendChatMessage);

    elements.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    elements.toggleChat.addEventListener('click', () => {
        elements.chatSection.classList.add('hidden');
    });

    elements.openChatBtn.addEventListener('click', () => {
        elements.chatSection.classList.remove('hidden');
    });
}

async function sendChatMessage() {
    const message = elements.chatInput.value.trim();
    if (!message || !state.reportId) return;

    // Clear input
    elements.chatInput.value = '';

    // Add user message to UI
    addChatMessage('user', message);

    // Send to API
    try {
        const response = await fetch(`/api/reports/${state.reportId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        if (!response.ok) throw new Error('Chat request failed');

        const data = await response.json();
        addChatMessage('assistant', data.response.content);

    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('assistant', '抱歉，发生了错误。请稍后再试。');
    }
}

function addChatMessage(role, content) {
    // Remove welcome message if present
    const welcome = elements.chatMessages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${escapeHtml(content)}</div>`;

    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// ============================================
// History Panel
// ============================================

function initHistory() {
    elements.historyBtn.addEventListener('click', () => {
        elements.historySidebar.classList.remove('hidden');
        elements.historySidebar.classList.add('visible');
    });

    elements.closeHistory.addEventListener('click', () => {
        elements.historySidebar.classList.remove('visible');
        elements.historySidebar.classList.add('hidden');
    });

    elements.historySearch.addEventListener('input', (e) => {
        filterHistory(e.target.value);
    });
}

async function loadHistory() {
    try {
        const response = await fetch('/api/reports');
        if (!response.ok) return;

        const data = await response.json();
        renderHistoryList(data.reports);

    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function renderHistoryList(reports) {
    elements.historyList.innerHTML = '';

    if (!reports || reports.length === 0) {
        elements.historyList.innerHTML = '<p class="no-history">暂无历史记录</p>';
        return;
    }

    reports.forEach(report => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.dataset.id = report.id;

        const date = new Date(report.created_at);
        const dateStr = date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

        item.innerHTML = `
            <div class="history-item-title">${escapeHtml(report.title)}</div>
            <div class="history-item-meta">
                <span><i class="fas fa-clock"></i> ${dateStr}</span>
                <span><i class="fas fa-comments"></i> ${report.chat_count || 0}</span>
            </div>
        `;

        item.addEventListener('click', () => loadReport(report.id));
        elements.historyList.appendChild(item);
    });
}

function filterHistory(query) {
    const items = elements.historyList.querySelectorAll('.history-item');
    const lowerQuery = query.toLowerCase();

    items.forEach(item => {
        const title = item.querySelector('.history-item-title').textContent.toLowerCase();
        item.style.display = title.includes(lowerQuery) ? 'block' : 'none';
    });
}

async function loadReport(reportId) {
    try {
        showLoading('加载报告...');

        // Load English report
        const enResponse = await fetch(`/api/reports/${reportId}?lang=en`);
        const enData = await enResponse.json();

        // Load Chinese report
        const zhResponse = await fetch(`/api/reports/${reportId}?lang=zh`);
        const zhData = await zhResponse.json();

        state.reportId = reportId;
        state.uploadId = enData.upload_id || reportId;  // Set uploadId for image paths
        state.reports = {
            english: enData.report,
            chinese: zhData.report
        };

        // Update UI
        elements.landingSection.classList.add('hidden');
        elements.analysisSection.classList.remove('hidden');
        elements.reportPanel.classList.remove('hidden');
        elements.chatSection.classList.remove('hidden');
        elements.historySidebar.classList.remove('visible');

        // Mark all progress steps as completed
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.add('completed');
            step.querySelector('.step-status').textContent = '完成';
        });

        // Render reports
        elements.reportTitle.innerHTML = `<i class="fas fa-file-alt"></i> ${enData.title || 'Report'}`;
        renderReport('en', state.reports.english);
        renderReport('zh', state.reports.chinese);

        // Render specialist reports if available
        if (enData.specialist_reports) {
            state.specialistReports = enData.specialist_reports;
            renderSpecialistReports(enData.specialist_reports);
        }

        // Load chat history
        await loadChatHistory(reportId);

        hideLoading();

    } catch (error) {
        hideLoading();
        showToast('加载失败: ' + error.message, 'error');
    }
}

async function loadChatHistory(reportId) {
    try {
        const response = await fetch(`/api/reports/${reportId}/chat`);
        if (!response.ok) return;

        const data = await response.json();

        // Clear existing messages
        elements.chatMessages.innerHTML = '';

        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                addChatMessage(msg.role, msg.content);
            });
        } else {
            elements.chatMessages.innerHTML = `
                <div class="chat-welcome">
                    <i class="fas fa-robot"></i>
                    <p>你好！我已阅读了这篇论文的分析报告。有什么问题想问我吗？</p>
                </div>
            `;
        }

    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

// ============================================
// Utility Functions
// ============================================

function showToast(message, type = 'info') {
    const { toast } = elements;

    toast.className = `toast ${type}`;
    toast.querySelector('.toast-icon').className = `toast-icon fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}`;
    toast.querySelector('.toast-message').textContent = message;

    toast.classList.remove('hidden');
    toast.classList.add('visible');

    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.classList.add('hidden'), 300);
    }, 3000);
}

function showLoading(text = '加载中...') {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
