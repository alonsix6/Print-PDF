/**
 * PDF OCR Enhancement Tool - Frontend Application
 * Modern, interactive PDF processing interface
 */

// ========================================
// Configuration
// ========================================
const CONFIG = {
    // API URL - Change this to your Railway backend URL
    API_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : 'https://your-backend.railway.app', // TODO: Update with your Railway URL

    // Polling interval for status checks (ms)
    POLL_INTERVAL: 1000,

    // Maximum file size in MB
    MAX_FILE_SIZE_MB: 100,

    // Allowed file types
    ALLOWED_TYPES: ['application/pdf'],

    // Toast duration (ms)
    TOAST_DURATION: 5000
};

// ========================================
// State Management
// ========================================
const state = {
    selectedFile: null,
    taskId: null,
    isProcessing: false,
    pollInterval: null,
    options: {
        language: 'spa+eng',
        deskew: true,
        denoise: true,
        enhance_contrast: true,
        remove_background: false,
        target_dpi: 300,
        upscale_images: true,
        quality_preset: 'ebook',
        optimize_size: true,
        force_ocr: false,
        rotate_pages: true
    }
};

// ========================================
// DOM Elements
// ========================================
const elements = {
    // Upload
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    filePreview: document.getElementById('filePreview'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    fileRemove: document.getElementById('fileRemove'),
    uploadSection: document.getElementById('uploadSection'),

    // Options
    optionsToggle: document.getElementById('optionsToggle'),
    optionsPanel: document.getElementById('optionsPanel'),
    language: document.getElementById('language'),
    presetButtons: document.getElementById('presetButtons'),
    deskew: document.getElementById('deskew'),
    denoise: document.getElementById('denoise'),
    enhanceContrast: document.getElementById('enhanceContrast'),
    rotatePges: document.getElementById('rotatePges'),
    optimizeSize: document.getElementById('optimizeSize'),
    forceOcr: document.getElementById('forceOcr'),
    removeBackground: document.getElementById('removeBackground'),
    targetDpi: document.getElementById('targetDpi'),
    dpiValue: document.getElementById('dpiValue'),

    // Actions
    processBtn: document.getElementById('processBtn'),

    // Progress
    progressSection: document.getElementById('progressSection'),
    statusIcon: document.getElementById('statusIcon'),
    statusTitle: document.getElementById('statusTitle'),
    statusMessage: document.getElementById('statusMessage'),
    progressPercent: document.getElementById('progressPercent'),
    progressFill: document.getElementById('progressFill'),
    progressStep: document.getElementById('progressStep'),
    progressPages: document.getElementById('progressPages'),

    // Result
    resultSection: document.getElementById('resultSection'),
    resultCard: document.getElementById('resultCard'),
    resultTitle: document.getElementById('resultTitle'),
    resultMessage: document.getElementById('resultMessage'),
    resultStats: document.getElementById('resultStats'),
    statOriginalSize: document.getElementById('statOriginalSize'),
    statOutputSize: document.getElementById('statOutputSize'),
    statTime: document.getElementById('statTime'),
    statPages: document.getElementById('statPages'),
    downloadBtn: document.getElementById('downloadBtn'),
    newBtn: document.getElementById('newBtn'),

    // Theme
    themeToggle: document.getElementById('themeToggle'),

    // Toast
    toastContainer: document.getElementById('toastContainer')
};

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initEventListeners();
    initOptionsFromStorage();
});

function initEventListeners() {
    // Upload area events
    elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
    elements.uploadArea.addEventListener('dragover', handleDragOver);
    elements.uploadArea.addEventListener('dragleave', handleDragLeave);
    elements.uploadArea.addEventListener('drop', handleDrop);
    elements.fileInput.addEventListener('change', handleFileSelect);
    elements.fileRemove.addEventListener('click', handleFileRemove);

    // Options toggle
    elements.optionsToggle.addEventListener('click', toggleOptions);

    // Language select
    elements.language.addEventListener('change', (e) => {
        state.options.language = e.target.value;
        saveOptions();
    });

    // Preset buttons
    elements.presetButtons.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => selectPreset(btn.dataset.value));
    });

    // Toggle options
    elements.deskew.addEventListener('change', (e) => {
        state.options.deskew = e.target.checked;
        saveOptions();
    });
    elements.denoise.addEventListener('change', (e) => {
        state.options.denoise = e.target.checked;
        saveOptions();
    });
    elements.enhanceContrast.addEventListener('change', (e) => {
        state.options.enhance_contrast = e.target.checked;
        saveOptions();
    });
    elements.rotatePges.addEventListener('change', (e) => {
        state.options.rotate_pages = e.target.checked;
        saveOptions();
    });
    elements.optimizeSize.addEventListener('change', (e) => {
        state.options.optimize_size = e.target.checked;
        saveOptions();
    });
    elements.forceOcr.addEventListener('change', (e) => {
        state.options.force_ocr = e.target.checked;
        saveOptions();
    });
    elements.removeBackground.addEventListener('change', (e) => {
        state.options.remove_background = e.target.checked;
        saveOptions();
    });

    // DPI slider
    elements.targetDpi.addEventListener('input', (e) => {
        const value = e.target.value;
        elements.dpiValue.textContent = value;
        state.options.target_dpi = parseInt(value);
        saveOptions();
    });

    // Process button
    elements.processBtn.addEventListener('click', startProcessing);

    // Result buttons
    elements.downloadBtn.addEventListener('click', downloadFile);
    elements.newBtn.addEventListener('click', resetToUpload);

    // Theme toggle
    elements.themeToggle.addEventListener('click', toggleTheme);
}

// ========================================
// Theme Management
// ========================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else if (prefersDark) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// ========================================
// Options Management
// ========================================
function initOptionsFromStorage() {
    const savedOptions = localStorage.getItem('pdfOptions');
    if (savedOptions) {
        try {
            state.options = { ...state.options, ...JSON.parse(savedOptions) };
            applyOptionsToUI();
        } catch (e) {
            console.error('Failed to parse saved options:', e);
        }
    }
}

function saveOptions() {
    localStorage.setItem('pdfOptions', JSON.stringify(state.options));
}

function applyOptionsToUI() {
    elements.language.value = state.options.language;
    elements.deskew.checked = state.options.deskew;
    elements.denoise.checked = state.options.denoise;
    elements.enhanceContrast.checked = state.options.enhance_contrast;
    elements.rotatePges.checked = state.options.rotate_pages;
    elements.optimizeSize.checked = state.options.optimize_size;
    elements.forceOcr.checked = state.options.force_ocr;
    elements.removeBackground.checked = state.options.remove_background;
    elements.targetDpi.value = state.options.target_dpi;
    elements.dpiValue.textContent = state.options.target_dpi;

    // Update preset buttons
    selectPreset(state.options.quality_preset, false);
}

function toggleOptions() {
    elements.optionsToggle.classList.toggle('active');
    elements.optionsPanel.classList.toggle('active');
}

function selectPreset(value, save = true) {
    state.options.quality_preset = value;

    elements.presetButtons.querySelectorAll('.preset-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.value === value);
    });

    if (save) saveOptions();
}

// ========================================
// File Handling
// ========================================
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    elements.uploadArea.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    elements.uploadArea.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    elements.uploadArea.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        validateAndSetFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        validateAndSetFile(files[0]);
    }
}

function validateAndSetFile(file) {
    // Check file type
    if (!CONFIG.ALLOWED_TYPES.includes(file.type) && !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Por favor selecciona un archivo PDF', 'error');
        return;
    }

    // Check file size
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > CONFIG.MAX_FILE_SIZE_MB) {
        showToast(`El archivo es muy grande. Máximo ${CONFIG.MAX_FILE_SIZE_MB}MB`, 'error');
        return;
    }

    // Set file
    state.selectedFile = file;
    showFilePreview(file);
    elements.processBtn.disabled = false;

    showToast('Archivo listo para procesar', 'success');
}

function showFilePreview(file) {
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatFileSize(file.size);
    elements.uploadArea.classList.add('hidden');
    elements.filePreview.classList.remove('hidden');
}

function handleFileRemove(e) {
    e.stopPropagation();
    state.selectedFile = null;
    elements.fileInput.value = '';
    elements.uploadArea.classList.remove('hidden');
    elements.filePreview.classList.add('hidden');
    elements.processBtn.disabled = true;
}

// ========================================
// Processing
// ========================================
async function startProcessing() {
    if (!state.selectedFile || state.isProcessing) return;

    state.isProcessing = true;
    elements.processBtn.disabled = true;
    elements.processBtn.classList.add('loading');

    // Show progress section
    elements.progressSection.classList.remove('hidden');
    elements.resultSection.classList.add('hidden');
    updateProgress(0, 'Subiendo archivo...', 'Iniciando...');

    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', state.selectedFile);

        // Add options as query parameters
        const params = new URLSearchParams({
            language: state.options.language,
            deskew: state.options.deskew,
            denoise: state.options.denoise,
            enhance_contrast: state.options.enhance_contrast,
            remove_background: state.options.remove_background,
            target_dpi: state.options.target_dpi,
            upscale_images: state.options.upscale_images,
            quality_preset: state.options.quality_preset,
            optimize_size: state.options.optimize_size,
            force_ocr: state.options.force_ocr,
            rotate_pages: state.options.rotate_pages
        });

        const uploadResponse = await fetch(`${CONFIG.API_URL}/api/upload?${params}`, {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail?.message || error.detail || 'Error al subir el archivo');
        }

        const uploadData = await uploadResponse.json();
        state.taskId = uploadData.task_id;

        updateProgress(10, 'Archivo subido', 'Iniciando procesamiento...');

        // Start polling for status
        startStatusPolling();

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message);
    }
}

function startStatusPolling() {
    state.pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${CONFIG.API_URL}/api/status/${state.taskId}`);

            if (!response.ok) {
                throw new Error('Error al obtener el estado');
            }

            const data = await response.json();
            handleStatusUpdate(data);

        } catch (error) {
            console.error('Status poll error:', error);
            // Don't stop polling on transient errors
        }
    }, CONFIG.POLL_INTERVAL);
}

function stopStatusPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
    }
}

function handleStatusUpdate(data) {
    const { status, progress, current_step, message, pages_processed, total_pages } = data;

    // Update progress UI
    updateProgress(
        progress,
        current_step,
        message,
        pages_processed,
        total_pages
    );

    // Handle completion
    if (status === 'completed') {
        stopStatusPolling();
        showSuccess(data);
    } else if (status === 'failed') {
        stopStatusPolling();
        showError(data.error_details || data.message || 'El procesamiento falló');
    }
}

function updateProgress(percent, step, message, pagesProcessed = null, totalPages = null) {
    elements.progressPercent.textContent = `${percent}%`;
    elements.progressFill.style.width = `${percent}%`;
    elements.progressStep.textContent = step;
    elements.statusMessage.textContent = message;

    if (totalPages !== null && totalPages > 0) {
        elements.progressPages.textContent = `${pagesProcessed}/${totalPages} páginas`;
    } else {
        elements.progressPages.textContent = '';
    }
}

// ========================================
// Results
// ========================================
function showSuccess(data) {
    state.isProcessing = false;
    elements.processBtn.classList.remove('loading');

    // Hide progress, show result
    elements.progressSection.classList.add('hidden');
    elements.resultSection.classList.remove('hidden');

    // Update result card
    elements.resultCard.classList.remove('error');
    elements.resultCard.classList.add('success');
    elements.resultTitle.textContent = '¡Procesamiento completado!';
    elements.resultMessage.textContent = 'Tu PDF ha sido mejorado con éxito y está listo para descargar.';

    // Update stats
    elements.statOriginalSize.textContent = formatFileSize(data.file_size_original);
    elements.statOutputSize.textContent = formatFileSize(data.file_size_output);
    elements.statTime.textContent = `${data.processing_time_seconds.toFixed(1)}s`;
    elements.statPages.textContent = data.total_pages;

    // Calculate compression
    if (data.file_size_original > 0 && data.file_size_output > 0) {
        const ratio = ((1 - data.file_size_output / data.file_size_original) * 100).toFixed(1);
        if (ratio > 0) {
            elements.statOutputSize.textContent += ` (-${ratio}%)`;
        }
    }

    showToast('¡PDF procesado exitosamente!', 'success');
}

function showError(message) {
    state.isProcessing = false;
    elements.processBtn.classList.remove('loading');
    elements.processBtn.disabled = false;

    // Hide progress, show result
    elements.progressSection.classList.add('hidden');
    elements.resultSection.classList.remove('hidden');

    // Update result card for error
    elements.resultCard.classList.remove('success');
    elements.resultCard.classList.add('error');
    elements.resultTitle.textContent = 'Error en el procesamiento';
    elements.resultMessage.textContent = message;
    elements.resultStats.classList.add('hidden');
    elements.downloadBtn.classList.add('hidden');

    showToast(message, 'error');
}

function downloadFile() {
    if (!state.taskId) return;

    const downloadUrl = `${CONFIG.API_URL}/api/download/${state.taskId}`;

    // Create temporary link and click it
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast('Descarga iniciada', 'success');
}

function resetToUpload() {
    // Reset state
    state.selectedFile = null;
    state.taskId = null;
    state.isProcessing = false;
    stopStatusPolling();

    // Reset UI
    elements.fileInput.value = '';
    elements.uploadArea.classList.remove('hidden');
    elements.filePreview.classList.add('hidden');
    elements.progressSection.classList.add('hidden');
    elements.resultSection.classList.add('hidden');
    elements.resultStats.classList.remove('hidden');
    elements.downloadBtn.classList.remove('hidden');
    elements.processBtn.disabled = true;
    elements.processBtn.classList.remove('loading');

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========================================
// Toast Notifications
// ========================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;

    // Add close functionality
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });

    elements.toastContainer.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, CONFIG.TOAST_DURATION);
}

// ========================================
// Utilities
// ========================================
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ========================================
// API Health Check
// ========================================
async function checkAPIHealth() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/health`);
        const data = await response.json();

        if (data.status !== 'healthy') {
            console.warn('API health check: degraded', data);
        }

        return data;
    } catch (error) {
        console.error('API health check failed:', error);
        return null;
    }
}

// Check API on load
checkAPIHealth().then(health => {
    if (!health) {
        showToast('Conectando con el servidor...', 'warning');
    }
});
