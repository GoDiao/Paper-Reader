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
    currentLang: 'en',
    uiLang: localStorage.getItem('uiLang') || 'en',  // UI language preference
    theme: localStorage.getItem('uiTheme') || 'dark'  // Theme preference
};

// Internationalization translations
const translations = {
    en: {
        // Header
        history: 'History',

        // Landing
        hero_title_1: 'AI-Powered',
        hero_title_2: 'Academic Paper Analyzer',
        hero_subtitle: 'Upload a PDF paper, AI automatically extracts key information and generates bilingual analysis reports',
        upload_text: 'Drag and drop PDF file here, or click to upload',
        upload_hint: 'Supports .pdf format, max 50MB',
        analysis_settings: 'Analysis Settings',
        analysis_mode: 'Analysis Mode',
        mode_hierarchical: 'Hierarchical (1+3+1 Agent Team)',
        mode_simple: 'Simple (Dual Role)',
        llm_provider: 'LLM Provider',
        model: 'Model',
        parser_backend: 'Parser Backend',
        parser_auto: 'Auto (Default)',
        enable_web_search: 'Enable Web Search',
        enable_web_search_hint: 'Search GitHub/HuggingFace for reproduction resources (code, models, datasets)',
        output_language: 'Output Language',
        language_en: 'English',
        language_zh: 'Chinese',
        start_analysis: 'Start Analysis',

        // Progress
        analysis_progress: 'Analysis Progress',
        pdf_parsing: 'PDF Parsing',
        waiting: 'Waiting...',

        // Report
        analysis_report: 'Analysis Report',
        chat_ai: 'Chat with AI',
        images: 'Images',
        copy: 'Copy',
        specialist_reports: 'Specialist Reports',
        
        // P0 Features
        variable_tracking: 'Variable Tracking',
        reproduction_checklist: 'Reproduction Checklist',
        datasets: 'Datasets',
        hyperparameters: 'Hyperparameters',
        hardware: 'Hardware Requirements',
        code_availability: 'Code Availability',
        risk_assessment: 'Risk Assessment',

        // Chat
        chat_with_paper: 'Chat with AI about Paper',
        
        // Variables Table
        var_symbol: 'Symbol',
        var_name: 'Name',
        var_definition: 'Definition',
        var_location: 'Location',
        var_value: 'Value',
        search_variables: 'Search variables...',
        chat_welcome: 'Hello! I have read the analysis of this paper. What questions do you have?',
        chat_placeholder: 'Type your question...',

        // Tooltips
        download_md: 'Download Markdown',
        download_pdf: 'Download PDF',
        download_word: 'Download Word',
        download_images: 'Download Images',
        copy_clipboard: 'Copy to Clipboard',
        chat_with_ai: 'Chat with AI about Paper',
        close_chat: 'Close Chat',
        send: 'Send',

        // Toast messages
        analysis_complete: 'Analysis Complete!',
        copied: 'Copied to clipboard!',
        analysis_complete: 'Analysis Complete!',
        completed: 'Completed',
        copied: 'Copied to clipboard!',
        copy_failed: 'Copy failed',
        pdf_dev_msg: 'Feature under development, please right click and use the print method.'
    },
    zh: {
        // Header
        history: '历史',

        // Landing
        hero_title_1: 'AI 驱动的',
        hero_title_2: '学术论文分析助手',
        hero_subtitle: '上传 PDF 论文，AI 自动提取关键信息，生成中英文双语分析报告',
        upload_text: '拖拽 PDF 文件到此处，或点击上传',
        upload_hint: '支持 .pdf 格式，最大 50MB',
        analysis_settings: '分析设置',
        analysis_mode: '分析模式',
        mode_hierarchical: '层级模式 (1+3+1 Agent Team)',
        mode_simple: '简单模式 (双角色)',
        llm_provider: 'LLM 提供商',
        model: '模型',
        parser_backend: '解析后端',
        parser_auto: '自动 (默认)',
        enable_web_search: '启用网络搜索',
        enable_web_search_hint: '搜索 GitHub/HuggingFace 获取复现资源（代码、模型、数据集）',
        output_language: '输出语言',
        language_en: '英语',
        language_zh: '中文',
        start_analysis: '开始分析',

        // Progress
        analysis_progress: '分析进度',
        step_editor: '编辑',
        pdf_parsing: 'PDF 解析',
        waiting: '等待中...',

        // Report
        analysis_report: '分析报告',
        chat_ai: '与AI讨论',
        images: '图片',
        copy: '复制',
        specialist_reports: '专家分析报告',
        
        // P0 Features
        variable_tracking: '变量追踪',
        reproduction_checklist: '复现清单',
        datasets: '数据集',
        hyperparameters: '超参数',
        hardware: '硬件要求',
        code_availability: '代码可用性',
        risk_assessment: '风险评估',

        // Chat
        chat_with_paper: '与 AI 讨论论文',

        // Variables Table
        var_symbol: '符号',
        var_name: '名称',
        var_definition: '定义',
        var_location: '位置',
        var_value: '值',
        search_variables: '搜索变量...',
        chat_welcome: '你好！我已阅读了这篇论文的分析报告。有什么问题想问我吗？',
        chat_placeholder: '输入你的问题...',

        // Tooltips
        download_md: '下载 Markdown',
        download_pdf: '下载 PDF',
        download_word: '下载 Word',
        download_images: '下载图片',
        copy_clipboard: '复制到剪贴板',
        chat_with_ai: '与AI讨论论文',
        close_chat: '关闭聊天',
        send: '发送',

        // Toast messages
        analysis_complete: '分析完成！',
        copied: '已复制到剪贴板！',
        analysis_complete: '分析完成！',
        completed: '已完成',
        copied: '已复制到剪贴板！',
        copy_failed: '复制失败',
        pdf_dev_msg: '功能正在开发，请右键使用print方法'
    }
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
    parserBackend: document.getElementById('parserBackend'),
    outputLanguage: document.getElementById('outputLanguage'),
    enableWebSearch: document.getElementById('enableWebSearch'),

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
    initI18n();  // Initialize language system first
    initTheme();  // Initialize theme system
    initUpload();
    initTabs();
    initExport();
    initChat();
    initHistory();
    initSpecialistReports();
    loadHistory();
});

// ============================================
// Internationalization (i18n)
// ============================================

function initI18n() {
    const langToggleBtn = document.getElementById('langToggleBtn');
    const langLabel = document.getElementById('langLabel');

    // Apply saved language on load
    applyLanguage(state.uiLang);

    // Toggle language on button click
    if (langToggleBtn) {
        langToggleBtn.addEventListener('click', () => {
            state.uiLang = state.uiLang === 'en' ? 'zh' : 'en';
            localStorage.setItem('uiLang', state.uiLang);
            applyLanguage(state.uiLang);
        });
    }
}

function applyLanguage(lang) {
    const t = translations[lang] || translations.en;
    const langLabel = document.getElementById('langLabel');

    // Update language button label
    if (langLabel) {
        langLabel.textContent = lang === 'en' ? 'EN' : '中';
    }

    // Update all elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            el.textContent = t[key];
        }
    });

    // Update all elements with data-i18n-title attribute  
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (t[key]) {
            el.setAttribute('title', t[key]);
        }
    });

    // Update all elements with data-i18n-placeholder attribute
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key]) {
            el.setAttribute('placeholder', t[key]);
        }
    });

    // Update select options with data-i18n
    document.querySelectorAll('option[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            el.textContent = t[key];
        }
    });
}

// ============================================
// Theme Management
// ============================================

function initTheme() {
    const themeToggleBtn = document.getElementById('themeToggleBtn');

    // Apply saved theme on load
    applyTheme(state.theme);

    // Toggle theme on button click
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            state.theme = state.theme === 'dark' ? 'light' : 'dark';
            localStorage.setItem('uiTheme', state.theme);
            applyTheme(state.theme);
        });
    }
}

function applyTheme(theme) {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = themeToggleBtn ? themeToggleBtn.querySelector('i') : null;

    // Set theme attribute on document
    document.documentElement.setAttribute('data-theme', theme);

    // Update button icon
    if (themeIcon) {
        if (theme === 'light') {
            themeIcon.className = 'fas fa-sun';
        } else {
            themeIcon.className = 'fas fa-moon';
        }
    }
}

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

    // Dynamic model filtering based on provider
    const llmProviderSelect = document.getElementById('llmProvider');
    const llmModelSelect = document.getElementById('llmModel');

    if (llmProviderSelect && llmModelSelect) {
        llmProviderSelect.addEventListener('change', () => {
            updateModelOptions(llmProviderSelect.value, llmModelSelect);
        });
        // Initialize with current provider selection
        updateModelOptions(llmProviderSelect.value, llmModelSelect);
    }
}

// Model options for each provider
const modelOptions = {
    deepseek: [
        { value: 'deepseek-chat', label: 'deepseek-chat' },
        { value: 'deepseek-reasoner', label: 'deepseek-r1 (Reasoning)' }
    ],
    openai: [
        { value: 'gpt-4o', label: 'gpt-4o' },
        { value: 'gpt-4o-mini', label: 'gpt-4o-mini' },
        { value: 'o1', label: 'o1 (Reasoning)' },
        { value: 'o1-mini', label: 'o1-mini' }
    ],
    siliconflow: [
        { value: 'deepseek-ai/DeepSeek-V3', label: 'DeepSeek-V3' },
        { value: 'deepseek-ai/DeepSeek-R1', label: 'DeepSeek-R1 (Reasoning)' },
        { value: 'deepseek-ai/DeepSeek-V3.2', label: 'DeepSeek-V3.2' },
        { value: 'Qwen/Qwen2.5-72B-Instruct', label: 'Qwen2.5-72B' },
        { value: 'Qwen/Qwen2.5-Coder-32B-Instruct', label: 'Qwen2.5-Coder-32B' },
        { value: 'MiniMaxAI/MiniMax-M2.1', label: 'MiniMax-M2.1' },
        { value: 'zai-org/GLM-4.7', label: 'GLM-4.7' },
        { value: 'moonshotai/Kimi-K2-Thinking', label: 'Kimi-K2 (Thinking)' }
    ]
};

function updateModelOptions(provider, selectElement) {
    const models = modelOptions[provider] || modelOptions.deepseek;
    selectElement.innerHTML = '';

    models.forEach((model, index) => {
        const option = document.createElement('option');
        option.value = model.value;
        option.textContent = model.label;
        if (index === 0) option.selected = true;
        selectElement.appendChild(option);
    });
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
    state.specialistReports = {}; // Reset reports
    connectWebSocket();
}

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${state.sessionId}`;

    state.websocket = new WebSocket(wsUrl);

    state.websocket.onopen = () => {
        console.log('WebSocket connected');

        // Send analysis request
        const enableWebSearch = elements.enableWebSearch ? elements.enableWebSearch.checked : false;
        state.websocket.send(JSON.stringify({
            type: 'analyze',
            upload_id: state.uploadId,
            mode: elements.analysisMode.value,
            provider: elements.llmProvider.value,
            model: elements.llmModel.value,
            verbose: false,
            parser: elements.parserBackend ? elements.parserBackend.value : 'auto',
            enable_web_search: enableWebSearch,
            language: elements.outputLanguage ? elements.outputLanguage.value : 'en'
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
        case 'stream':
            handleStreamMessage(data);
            break;
        case 'architect_plan':
            handleArchitectPlan(data);
            break;
    }
}

function handleArchitectPlan(data) {
    const { plan } = data;
    if (!plan) return;

    // Show specialist section if hidden
    const section = document.getElementById('specialistReportsSection');
    if (section.classList.contains('hidden')) {
        section.classList.remove('hidden');
        const content = document.getElementById('specialistContent');
        const toggle = document.getElementById('specialistToggle');
        content.classList.add('expanded');
        toggle.classList.add('expanded');
    }

    // Architect UI removed per user request
    // We just ensure the section is visible for other agents
}   

function formatArchitectPlan(plan) {
    let md = `### 📋 Research Plan\n\n`;
    md += `**Domain**: ${plan.domain}\n\n`;
    md += `**Summary**: ${plan.paper_summary}\n\n`;
    md += `---\n\n`;
    md += `### 🕵️ Agent Assignments\n\n`;

    // Context Hunter
    if (plan.context_hunter_task) {
        md += `#### 🔍 Context Hunter\n`;
        md += `- **Focus**: Background, Related Work, Motivation\n`;
        if (plan.context_hunter_task.sections) {
            md += `- **Sections**: ${plan.context_hunter_task.sections.join(', ')}\n`;
        }
        md += `\n`;
    }

    // Math Specialist
    if (plan.math_specialist_task) {
        md += `#### 🔢 Math Specialist\n`;
        md += `- **Focus**: Methodology, Algorithms, Equations\n`;
        if (plan.math_specialist_task.sections) {
            md += `- **Sections**: ${plan.math_specialist_task.sections.join(', ')}\n`;
        }
        md += `\n`;
    }

    // Data Auditor
    if (plan.data_auditor_task) {
        md += `#### 📊 Data Auditor\n`;
        md += `- **Focus**: Experiments, Results, Metrics\n`;
        if (plan.data_auditor_task.sections) {
            md += `- **Sections**: ${plan.data_auditor_task.sections.join(', ')}\n`;
        }
        md += `\n`;
    }

    return md;
}

function handleStreamMessage(data) {
    const { agent, token } = data;

    // Only handle specialist agents
    const validAgents = ['context_hunter', 'math_specialist', 'data_auditor'];
    if (!validAgents.includes(agent)) return;

    // Show specialist section if hidden
    const section = document.getElementById('specialistReportsSection');
    if (section.classList.contains('hidden')) {
        section.classList.remove('hidden');
        // Ensure content is visible (auto-expand)
        const content = document.getElementById('specialistContent');
        const toggle = document.getElementById('specialistToggle');
        if (!content.classList.contains('expanded')) {
            content.classList.add('expanded');
            toggle.classList.add('expanded');
        }
    }

    // Switch tab to the active agent if it's the first token or user hasn't manually switched?
    // For now, let's NOT auto-switch tabs to avoid annoying the user if they are reading another one.
    // However, if we are just starting, maybe we should? 
    // Let's at least ensure the container exists.

    const container = document.querySelector(`.specialist-report[data-specialist="${agent}"]`);
    if (!container) return;

    // Buffer content
    if (!state.specialistReports[agent]) {
        state.specialistReports[agent] = '';
    }
    state.specialistReports[agent] += token;

    // Render (throttled/managed)
    // For streaming efficiency, we might just append text node if it's simple text, 
    // but Markdown needs parsing. 
    // Full re-render on every token is expensive. 
    // Lets try simple text append for now, or throttled markdown render.
    // For this implementation, let's settle for simple re-render every X tokens or use a throttle function.
    // Given the complexity, let's just re-render. Modern browsers are fast enough for small docs.
    // If it lags, we can optimize.

    requestAnimationFrame(() => {
        renderSingleSpecialistReport(agent, state.specialistReports[agent]);
    });
}

function renderSingleSpecialistReport(agent, markdown) {
    const container = document.querySelector(`.specialist-report[data-specialist="${agent}"]`);
    if (!container) return;

    // Fix table formatting (ensure newline before table) same as final report
    markdown = markdown.replace(/\r\n/g, '\n');
    // Ensure blank line before tables
    markdown = markdown.replace(/([^\n])\n(\|.*\|[ \t]*\n\|[-:| ]+\|)/g, '$1\n\n$2');

    // CRITICAL: Protect LaTeX from Markdown processor
    // Use HTML comments as placeholders
    const mathBlocks = [];
    let mathIndex = 0;

    // Protect display math: $$...$$
    markdown = markdown.replace(/\$\$[\s\S]*?\$\$/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Protect display math: \[...\]
    markdown = markdown.replace(/\\\[[\s\S]*?\\\]/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Protect inline math: $...$
    // Be careful with single $ matching normal text.
    // We strictly match $...$ where ... contains no $ and no newlines (for inline)
    markdown = markdown.replace(/\$[^\$\n]+?\$/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Protect inline math: \(...\)
    markdown = markdown.replace(/\\\([\s\S]*?\\\)/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Basic Markdown to HTML
    let html = converter.makeHtml(markdown);

    // Restore LaTeX blocks from HTML comments
    html = html.replace(/<!--MATH(\d+)-->/g, (match, index) => {
        return mathBlocks[parseInt(index)] || match;
    });

    container.innerHTML = html;

    // Render LaTeX math
    // We do this on every frame update, which is heavy, but necessary for streaming math.
    // KaTeX is relatively fast.
    try {
        renderMathInElement(container, {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '\\[', right: '\\]', display: true },
                { left: '$', right: '$', display: false },
                { left: '\\(', right: '\\)', display: false }
            ],
            throwOnError: false,
            trust: true,
            strict: false
        });
    } catch (error) {
        // Suppress errors during partial rendering
    }
}

function updateProgress(data) {
    const { phase, agent, status, message } = data;

    // Auto-show specialist section when analysis starts (Global UI update)
    if (phase === 'analysis' && status === 'started') {
        const section = document.getElementById('specialistReportsSection');
        if (section && section.classList.contains('hidden')) {
            section.classList.remove('hidden');
            const content = document.getElementById('specialistContent');
            const toggle = document.getElementById('specialistToggle');
            if (content) content.classList.add('expanded');
            if (toggle) toggle.classList.add('expanded');
        }
    }

    // Find the matching step element
    let stepElement;

    if (phase === 'parsing') {
        stepElement = document.querySelector('.progress-step[data-phase="parsing"]');
    } else if (agent === 'editor_english' || agent === 'editor_chinese') {
        stepElement = document.querySelector('.progress-step[data-agent="editor"]');
    } else {
        stepElement = document.querySelector(`.progress-step[data-agent="${agent}"]`);
    }

    if (!stepElement) {
        // Fallback for hidden agents (like Architect) - ensure errors are visible
        if (status === 'error') {
            showToast(`Error in ${agent}: ${message}`, 'error');
        }
        return;
    }

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

    // Only mark steps as completed if they're still waiting/active (fallback)
    // Real-time progress events should have already updated most steps
    const allSteps = document.querySelectorAll('.progress-step');
    allSteps.forEach(step => {
        // Only update if step is still in waiting/active state (not already completed)
        if (!step.classList.contains('completed') && !step.classList.contains('error')) {
            step.classList.remove('active');
            step.classList.add('completed');
            const statusEl = step.querySelector('.step-status');
            if (statusEl) {
                // Only update if status is still "Waiting..." or generic
                const currentText = statusEl.textContent.toLowerCase();
                const i18nKey = statusEl.getAttribute('data-i18n');
                if (i18nKey === 'waiting' || currentText.includes('waiting') || currentText === '') {
                    statusEl.setAttribute('data-i18n', 'completed');
                    statusEl.textContent = translations[state.uiLang].completed;
                }
                // Otherwise keep the more specific message from progress events
            }
        }
    });

    // Show report panel
    elements.reportPanel.classList.remove('hidden');

    // Update title
    if (metadata.title) {
        elements.reportTitle.innerHTML = `<i class="fas fa-file-alt"></i> ${metadata.title}`;
    }

    // Render reports and manage tabs
    const enTab = document.querySelector('.tab-btn[data-lang="en"]');
    const zhTab = document.querySelector('.tab-btn[data-lang="zh"]');
    const tabContainer = document.querySelector('.report-tabs');
    
    let reportCount = 0;

    if (reports.english) {
        renderReport('en', reports.english);
        if (enTab) enTab.style.display = 'inline-flex';
        reportCount++;
    } else {
        if (enTab) enTab.style.display = 'none';
    }
    
    if (reports.chinese) {
        renderReport('zh', reports.chinese);
        if (zhTab) zhTab.style.display = 'inline-flex';
        reportCount++;
    } else {
        if (zhTab) zhTab.style.display = 'none';
    }
    
    // Hide tab container if only one report
    if (tabContainer) {
        if (reportCount <= 1) {
            tabContainer.style.display = 'none';
        } else {
            tabContainer.style.display = 'flex';
        }
    }

    // Auto-select the available tab
    if (reports.english && !reports.chinese) {
        enTab.click();
    } else if (!reports.english && reports.chinese) {
        zhTab.click();
    } else {
        // If both or neither (fallback), default to English or UI language
        if (state.uiLang === 'zh' && reports.chinese) {
            zhTab.click();
        } else {
            enTab.click();
        }
    }

    // Render specialist reports if available
    console.log('[handleAnalysisComplete] metadata:', metadata);
    console.log('[handleAnalysisComplete] specialist_reports:', metadata.specialist_reports);
    if (metadata.specialist_reports) {
        state.specialistReports = metadata.specialist_reports;
        renderSpecialistReports(metadata.specialist_reports);
    }

    // Render P0 features: Variable Tracking and Reproduction Checklist
    if (metadata.variable_tracking || metadata.reproduction_checklist) {
        renderP0Features(metadata.variable_tracking, metadata.reproduction_checklist);
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

    // Protect display math: \[...\]
    markdown = markdown.replace(/\\\[[\s\S]*?\\\]/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Protect inline math: $...$
    markdown = markdown.replace(/\$[^\$\n]+?\$/g, (match) => {
        mathBlocks.push(match);
        return `<!--MATH${mathIndex++}-->`;
    });

    // Protect inline math: \(...\)
    markdown = markdown.replace(/\\\([\s\S]*?\\\)/g, (match) => {
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

    // Resize functionality
    initSpecialistResize();
}

function initSpecialistResize() {
    const handle = document.getElementById('specialistResizeHandle');
    const content = document.getElementById('specialistReportContent');
    
    if (!handle || !content) return;

    let isResizing = false;
    let startY = 0; // Initial mouse PageY
    let startHeight = 0; // Initial content height
    let lastClientY = 0; // Current mouse ClientY (viewport)
    let autoScrollRaf = null;

    // Helper: Update height based on current scroll position
    const updateHeight = () => {
        const currentPageY = lastClientY + window.scrollY;
        const deltaY = currentPageY - startY;
        const newHeight = Math.max(200, startHeight + deltaY);
        content.style.height = `${newHeight}px`;
        content.style.maxHeight = 'none';
    };

    // Helper: Auto-scroll loop
    const startAutoScroll = () => {
        if (autoScrollRaf) return;

        const loop = () => {
            const edgeThreshold = 50;
            const scrollStep = 15;
            let scrolled = false;

            if (lastClientY > window.innerHeight - edgeThreshold) {
                window.scrollBy(0, scrollStep);
                scrolled = true;
            } else if (lastClientY < edgeThreshold) {
                window.scrollBy(0, -scrollStep);
                scrolled = true;
            }

            if (scrolled) {
                updateHeight(); // Sync height with new scroll position
                autoScrollRaf = requestAnimationFrame(loop);
            } else {
                stopAutoScroll();
            }
        };
        autoScrollRaf = requestAnimationFrame(loop);
    };

    const stopAutoScroll = () => {
        if (autoScrollRaf) {
            cancelAnimationFrame(autoScrollRaf);
            autoScrollRaf = null;
        }
    };

    handle.addEventListener('mousedown', (e) => {
        isResizing = true;
        // Capture initial state
        startY = e.pageY;
        startHeight = content.getBoundingClientRect().height;
        lastClientY = e.clientY;
        
        // Add styling
        document.body.style.cursor = 'row-resize';
        document.body.classList.add('resizing');
        handle.classList.add('active');
        
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        lastClientY = e.clientY;
        updateHeight();
        startAutoScroll(); // Check if we need to start scrolling
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            stopAutoScroll();
            
            document.body.style.cursor = '';
            document.body.classList.remove('resizing');
            handle.classList.remove('active');
        }
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

        // Fix table formatting: ensure there is a blank line before each table header row
        // 1. Normalize line endings to \n
        markdown = markdown.replace(/\r\n/g, '\n');

        // 2. Insert blank line before table if missing.
        // Matches: (Non-newline char) -> \n -> (Table Header) -> \n -> (Table Separator)
        markdown = markdown.replace(/([^\n])\n(\|.*\|[ \t]*\n\|[-:| ]+\|)/g, '$1\n\n$2');

        // CRITICAL: Protect LaTeX from Markdown processor (same as main reports)
        const mathBlocks = [];
        let mathIndex = 0;

        // Protect display math: $$...$$
        markdown = markdown.replace(/\$\$[\s\S]*?\$\$/g, (match) => {
            mathBlocks.push(match);
            return `<!--MATH${mathIndex++}-->`;
        });

        // Protect display math: \[...\]
        markdown = markdown.replace(/\\\[[\s\S]*?\\\]/g, (match) => {
            mathBlocks.push(match);
            return `<!--MATH${mathIndex++}-->`;
        });

        // Protect inline math: $...$
        markdown = markdown.replace(/\$[^\$\n]+?\$/g, (match) => {
            mathBlocks.push(match);
            return `<!--MATH${mathIndex++}-->`;
        });

        // Protect inline math: \(...\)
        markdown = markdown.replace(/\\\([\s\S]*?\\\)/g, (match) => {
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
// P0 Features: Variable Tracking & Reproduction Checklist
// ============================================

function renderP0Features(variableTracking, reproductionChecklist) {
    const p0Section = document.getElementById('p0FeaturesSection');
    if (!p0Section) return;

    // Show the P0 features section
    p0Section.classList.remove('hidden');

    // Render Variable Tracking
    if (variableTracking && variableTracking.variables && variableTracking.variables.length > 0) {
        renderVariableTracking(variableTracking);
    }

    // Render Reproduction Checklist
    if (reproductionChecklist) {
        renderReproductionChecklist(reproductionChecklist);
    }
}

function renderVariableTracking(data) {
    const panel = document.getElementById('variableTrackingPanel');
    if (!panel) return;

    panel.classList.remove('hidden');

    // Update count badge
    const countBadge = document.getElementById('variableCount');
    if (countBadge) {
        countBadge.textContent = `(${data.variables.length})`;
    }

    // Render variable table
    const tbody = document.getElementById('variableTableBody');
    if (tbody && data.variables) {
        tbody.innerHTML = data.variables.map(v => `
            <tr>
                <td>${escapeHtml(v.symbol || '')}</td>
                <td>${escapeHtml(v.name || '')}</td>
                <td>${escapeHtml(v.definition || '')}</td>
                <td>${escapeHtml(v.location || '')}</td>
                <td>${escapeHtml(v.value || '-')}</td>
            </tr>
        `).join('');
    }

    // Render dependency graph
    const graphContainer = document.getElementById('dependencyGraph');
    const graphContent = document.getElementById('dependencyGraphContent');
    if (graphContainer && graphContent && data.dependency_graph) {
        graphContainer.classList.remove('hidden');
        graphContent.textContent = data.dependency_graph;
    }

    // Setup toggle
    const toggle = document.getElementById('variableToggle');
    const content = document.getElementById('variableContent');
    if (toggle && content) {
        toggle.addEventListener('click', () => {
            toggle.classList.toggle('expanded');
            content.classList.toggle('expanded');
        });
        // Auto-expand by default
        toggle.classList.add('expanded');
        content.classList.add('expanded');
    }

    // Setup search
    const searchInput = document.getElementById('variableSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const rows = tbody.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }
}

function renderReproductionChecklist(data) {
    const panel = document.getElementById('reproductionChecklistPanel');
    if (!panel) return;

    panel.classList.remove('hidden');

    // Render datasets
    if (data.datasets && data.datasets.length > 0) {
        renderChecklistTable('datasetsTable', data.datasets, ['dataset', 'size', 'access', 'download_link', 'notes']);
    }

    // Render hyperparameters
    if (data.hyperparameters && data.hyperparameters.length > 0) {
        renderChecklistTable('hyperparametersTable', data.hyperparameters, ['parameter', 'value', 'location', 'reproducibility']);
    }

    // Render hardware
    if (data.hardware && data.hardware.length > 0) {
        renderChecklistTable('hardwareTable', data.hardware, ['resource', 'requirement', 'location']);
    }

    // Render code availability
    if (data.code_availability && Object.keys(data.code_availability).length > 0) {
        renderCodeAvailability(data.code_availability);
    }

    // Render risk assessment
    if (data.risk_assessment && data.risk_assessment.length > 0) {
        renderRiskAssessment(data.risk_assessment);
    }

    // Setup toggle
    const toggle = document.getElementById('checklistToggle');
    const content = document.getElementById('checklistContent');
    if (toggle && content) {
        toggle.addEventListener('click', () => {
            toggle.classList.toggle('expanded');
            content.classList.toggle('expanded');
        });
        // Auto-expand by default
        toggle.classList.add('expanded');
        content.classList.add('expanded');
    }
}

function renderChecklistTable(containerId, data, columns) {
    const container = document.getElementById(containerId);
    if (!container || !data || data.length === 0) return;

    // Generate header labels from column names
    const headerLabels = columns.map(c => c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));

    let html = '<table><thead><tr>';
    headerLabels.forEach(label => {
        html += `<th>${label}</th>`;
    });
    html += '</tr></thead><tbody>';

    data.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            const value = row[col] || '-';
            html += `<td>${escapeHtml(value)}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderCodeAvailability(data) {
    const container = document.getElementById('codeAvailabilityContent');
    if (!container) return;

    let html = '';
    Object.entries(data).forEach(([key, info]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        const status = info.status || '';
        const link = info.link || '';

        let statusClass = 'unknown';
        let statusIcon = 'fa-question-circle';
        if (status.includes('✅') || status.toLowerCase().includes('available')) {
            statusClass = 'available';
            statusIcon = 'fa-check-circle';
        } else if (status.includes('❌') || status.toLowerCase().includes('not')) {
            statusClass = 'unavailable';
            statusIcon = 'fa-times-circle';
        } else if (status.includes('🔍')) {
            statusClass = 'unknown';
            statusIcon = 'fa-search';
        }

        html += `
            <div class="code-availability-item">
                <span class="label">${label}</span>
                <span class="status ${statusClass}">
                    <i class="fas ${statusIcon}"></i>
                    ${escapeHtml(status)}
                    ${link ? `<a href="${escapeHtml(link)}" target="_blank" rel="noopener">Link</a>` : ''}
                </span>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderRiskAssessment(data) {
    const container = document.getElementById('riskTable');
    if (!container || !data || data.length === 0) return;

    let html = '<table><thead><tr><th>Risk</th><th>Level</th><th>Reason</th></tr></thead><tbody>';

    data.forEach(row => {
        const level = (row.level || 'unknown').toLowerCase();
        const levelClass = level.includes('low') || level.includes('🟢') ? 'low' :
                          level.includes('medium') || level.includes('🟡') ? 'medium' :
                          level.includes('high') || level.includes('🔴') ? 'high' : 'unknown';

        html += `
            <tr>
                <td>${escapeHtml(row.risk || row.name || '-')}</td>
                <td><span class="risk-level ${levelClass}">${escapeHtml(row.level || '-')}</span></td>
                <td>${escapeHtml(row.reason || '-')}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ============================================
// Export Functions
// ============================================

function initExport() {
    const exportBtns = document.querySelectorAll('.export-btn[data-format]');

    exportBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const format = btn.dataset.format;
            
            // PDF button specific behavior
            if (format === 'pdf') {
                const t = translations[state.uiLang] || translations.en;
                const msg = t.pdf_dev_msg;
                showToast(msg, 'info');
                return;
            }

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
    if (elements.sendChatBtn) {
        elements.sendChatBtn.addEventListener('click', sendChatMessage);
    }

    if (elements.chatInput) {
        elements.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });

        // Auto-resize textarea
        elements.chatInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
            if (this.value === '') this.style.height = '';
        });
    }

    if (elements.openChatBtn) {
        elements.openChatBtn.addEventListener('click', () => {
            const chatSection = document.getElementById('chatSection');
            if (chatSection) {
                chatSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Focus input
                if (elements.chatInput) setTimeout(() => elements.chatInput.focus(), 500);
            }
        });
    }
}

async function sendChatMessage() {
    const message = elements.chatInput.value.trim();
    if (!message || !state.reportId) return;

    // Clear input & reset height
    elements.chatInput.value = '';
    elements.chatInput.style.height = '';

    // Add user message to UI
    addChatMessage('user', message);

    // Add placeholder for assistant
    const responseDiv = addChatMessage('assistant', '');
    const contentDiv = responseDiv.querySelector('.message-content');
    contentDiv.innerHTML = '<span class="typing">Thinking...</span>';

    // Initialize converter
    const converter = new showdown.Converter({
        tables: true,
        strikethrough: true,
        tasklists: true
    });

    // Send to API
    try {
        const response = await fetch(`/api/reports/${state.reportId}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        if (!response.ok) throw new Error('Chat request failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            fullContent += text;

            // Protect Math
            const mathBlocks = [];
            let mathIndex = 0;
            let protectedContent = fullContent
                .replace(/\$\$[\s\S]*?\$\$/g, (match) => {
                    mathBlocks.push(match);
                    return `<!--MATH${mathIndex++}-->`;
                })
                .replace(/\$[^\$\n]+?\$/g, (match) => {
                    mathBlocks.push(match);
                    return `<!--MATH${mathIndex++}-->`;
                });

            // Render markdown using Showdown
            let html = converter.makeHtml(protectedContent);

            // Restore Math
            html = html.replace(/<!--MATH(\d+)-->/g, (match, index) => {
                return mathBlocks[parseInt(index)] || match;
            });

            contentDiv.innerHTML = html;

            // Highlight code blocks
            contentDiv.querySelectorAll('pre code').forEach(block => {
                if (typeof hljs !== 'undefined') hljs.highlightElement(block);
            });

            // Re-render math
            if (typeof renderMathInElement !== 'undefined') {
                renderMathInElement(contentDiv, {
                    delimiters: [
                        { left: '$$', right: '$$', display: true },
                        { left: '$', right: '$', display: false }
                    ],
                    throwOnError: false
                });
            }


            // Scroll to bottom
            elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        }

    } catch (error) {
        console.error('Chat error:', error);
        contentDiv.innerHTML += '<br><span style="color:var(--error)">[Error: Request failed. Please try again.]</span>';
    }
}

function addChatMessage(role, content) {
    // Remove welcome message if present
    const welcome = elements.chatMessages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    let innerHTML = '';
    if (role === 'user') {
        innerHTML = `<div class="message-content">${escapeHtml(content)}</div>`;
    } else {
        // Assistant message - potentially markdown
        if (content) {
            const converter = new showdown.Converter({
                tables: true,
                strikethrough: true,
                tasklists: true
            });

            // Protect Math
            const mathBlocks = [];
            let mathIndex = 0;
            let protectedContent = content
                .replace(/\$\$[\s\S]*?\$\$/g, (match) => {
                    mathBlocks.push(match);
                    return `<!--MATH${mathIndex++}-->`;
                })
                .replace(/\$[^\$\n]+?\$/g, (match) => {
                    mathBlocks.push(match);
                    return `<!--MATH${mathIndex++}-->`;
                });

            let html = converter.makeHtml(protectedContent);

            // Restore Math
            html = html.replace(/<!--MATH(\d+)-->/g, (match, index) => {
                return mathBlocks[parseInt(index)] || match;
            });

            innerHTML = `<div class="message-content markdown-body">${html}</div>`;
        } else {
            innerHTML = `<div class="message-content"></div>`;
        }
    }

    messageDiv.innerHTML = innerHTML;
    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;

    return messageDiv;
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
