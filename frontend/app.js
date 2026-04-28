/**
 * ScanVD — Video Content Scanner
 * Frontend application logic
 */

const API_BASE = '';

// ----- DOM Elements -----
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const progressContainer = document.getElementById('progress-container');
const fileName = document.getElementById('file-name');
const progressStatus = document.getElementById('progress-status');
const progressFill = document.getElementById('progress-fill');
const stepUpload = document.getElementById('step-upload');
const stepTranscribe = document.getElementById('step-transcribe');
const stepReady = document.getElementById('step-ready');

const uploadSection = document.getElementById('upload-section');
const searchSection = document.getElementById('search-section');
const videoPlayer = document.getElementById('video-player');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');

const transcriptBtn = document.getElementById('transcript-btn');
const transcriptContent = document.getElementById('transcript-content');
const transcriptText = document.getElementById('transcript-text');

const resultsContainer = document.getElementById('results-container');
const resultsTitle = document.getElementById('results-title');
const resultsCount = document.getElementById('results-count');
const resultsList = document.getElementById('results-list');
const noResults = document.getElementById('no-results');

const newVideoBtn = document.getElementById('new-video-btn');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');

// ----- State -----
let currentVideoId = null;
let transcriptionData = null;

// ----- Toast -----
function showToast(message, type = 'info') {
    toastMessage.textContent = message;
    toast.className = `toast ${type}`;
    // Force reflow for animation
    setTimeout(() => toast.classList.add('visible'), 10);
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.classList.add('hidden'), 300);
    }, 4000);
}

// ----- Upload Zone Events -----
uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// ----- Handle File Upload -----
async function handleFile(file) {
    // Validate
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/quicktime',
                          'video/x-msvideo', 'video/x-matroska', 'video/webm',
                          'video/x-flv', 'video/x-ms-wmv'];
    
    if (!file.type.startsWith('video/')) {
        showToast('Please select a video file', 'error');
        return;
    }

    if (file.size > 500 * 1024 * 1024) {
        showToast('File size must be under 500MB', 'error');
        return;
    }

    // Show progress
    uploadZone.style.display = 'none';
    progressContainer.classList.remove('hidden');
    fileName.textContent = file.name;
    progressStatus.textContent = 'Uploading...';
    progressFill.style.width = '0%';

    // Reset steps
    stepUpload.className = 'progress-step active';
    stepTranscribe.className = 'progress-step';
    stepReady.className = 'progress-step';

    try {
        // Simulate upload progress
        const uploadProgress = setInterval(() => {
            const current = parseFloat(progressFill.style.width) || 0;
            if (current < 40) {
                progressFill.style.width = `${current + 2}%`;
            }
        }, 100);

        // Upload file
        const formData = new FormData();
        formData.append('file', file);

        // Move to transcribing
        setTimeout(() => {
            clearInterval(uploadProgress);
            progressFill.style.width = '45%';
            progressStatus.textContent = 'Analyzing audio & objects...';
            stepUpload.className = 'progress-step done';
            stepTranscribe.className = 'progress-step active';

            // Slow progress for transcription
            const transcribeProgress = setInterval(() => {
                const current = parseFloat(progressFill.style.width) || 0;
                if (current < 85) {
                    progressFill.style.width = `${current + 0.5}%`;
                }
            }, 500);

            // Store the interval for cleanup
            window._transcribeProgress = transcribeProgress;
        }, 1500);

        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        // Clear transcribe progress
        if (window._transcribeProgress) {
            clearInterval(window._transcribeProgress);
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        const data = await response.json();
        currentVideoId = data.video_id;

        // Complete progress
        progressFill.style.width = '100%';
        progressStatus.textContent = 'Ready!';
        stepTranscribe.className = 'progress-step done';
        stepReady.className = 'progress-step done';

        // Load transcription
        await loadTranscription(currentVideoId);

        // Switch to search view
        setTimeout(() => {
            showSearchSection(file);
        }, 1000);

    } catch (error) {
        console.error('Upload error:', error);
        showToast(error.message || 'Upload failed. Is the server running?', 'error');
        
        // Reset
        progressContainer.classList.add('hidden');
        uploadZone.style.display = '';
    }
}

// ----- Load Transcription -----
async function loadTranscription(videoId) {
    try {
        const response = await fetch(`${API_BASE}/api/transcript/${videoId}`);
        if (!response.ok) throw new Error('Failed to load transcript');

        transcriptionData = await response.json();

        // Build transcript view
        buildTranscriptView(transcriptionData.segments);

    } catch (error) {
        console.error('Transcript error:', error);
    }
}

function buildTranscriptView(segments) {
    transcriptText.innerHTML = '';

    segments.forEach(seg => {
        const timestamp = document.createElement('span');
        timestamp.className = 'timestamp';
        timestamp.textContent = `[${seg.start_formatted}]`;
        timestamp.addEventListener('click', () => jumpToTime(seg.start));

        const text = document.createElement('span');
        text.className = 'segment';
        text.textContent = ` ${seg.text} `;
        text.addEventListener('click', () => jumpToTime(seg.start));

        transcriptText.appendChild(timestamp);
        transcriptText.appendChild(text);
    });
}

// ----- Show Search Section -----
function showSearchSection(file) {
    uploadSection.classList.add('hidden');
    searchSection.classList.remove('hidden');

    // Set video source
    const videoUrl = `${API_BASE}/api/video/${currentVideoId}`;
    videoPlayer.src = videoUrl;
    videoPlayer.load();

    // Focus search input
    searchInput.focus();
}

// ----- Jump to Time -----
function jumpToTime(seconds) {
    videoPlayer.currentTime = seconds;
    videoPlayer.play();
    videoPlayer.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ----- Search -----
searchBtn.addEventListener('click', performSearch);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        showToast('Type something to search for', 'error');
        searchInput.focus();
        return;
    }

    if (!currentVideoId) {
        showToast('Please upload a video first', 'error');
        return;
    }

    // Loading state
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<div class="spinner"></div> Searching...';

    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: currentVideoId,
                query: query,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Search failed');
        }

        const data = await response.json();
        displayResults(data, query);

    } catch (error) {
        console.error('Search error:', error);
        showToast(error.message || 'Search failed', 'error');
    } finally {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<span>Search</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
    }
}

// ----- Display Results -----
function displayResults(data, query) {
    noResults.classList.add('hidden');
    resultsContainer.classList.add('hidden');
    resultsList.innerHTML = '';

    if (data.result_count === 0) {
        noResults.classList.remove('hidden');
        return;
    }

    resultsContainer.classList.remove('hidden');
    resultsTitle.textContent = `Results for "${query}"`;
    resultsCount.textContent = `${data.result_count} found`;

    data.results.forEach((result, index) => {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.style.animationDelay = `${index * 0.08}s`;

        const startTime = result.precise_start_formatted || result.start_formatted;
        const jumpTime = result.precise_start !== undefined ? result.precise_start : result.start;

        // Highlight matching text
        const highlightedText = highlightQuery(result.text, query);

        let matchLabel = 'Exact Match';
        let matchClass = 'exact';
        
        if (result.match_type === 'partial') {
            matchLabel = 'Partial Match';
            matchClass = 'partial';
        } else if (result.match_type === 'object') {
            matchLabel = 'Object Match';
            matchClass = 'object';
        }

        card.innerHTML = `
            <div class="result-time">
                <div class="result-timestamp">${startTime}</div>
                <svg class="result-play-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
            </div>
            <div class="result-body">
                <div class="result-text">${highlightedText}</div>
                <span class="result-match-type ${matchClass}">${matchLabel}</span>
            </div>
        `;

        card.addEventListener('click', () => jumpToTime(jumpTime));
        resultsList.appendChild(card);
    });
}

function highlightQuery(text, query) {
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ----- Transcript Toggle -----
transcriptBtn.addEventListener('click', () => {
    const isOpen = transcriptBtn.classList.toggle('open');
    if (isOpen) {
        transcriptContent.classList.remove('hidden');
        transcriptBtn.querySelector('span').textContent = 'Hide Full Transcript';
    } else {
        transcriptContent.classList.add('hidden');
        transcriptBtn.querySelector('span').textContent = 'Show Full Transcript';
    }
});

// ----- New Video -----
newVideoBtn.addEventListener('click', () => {
    // Reset state
    currentVideoId = null;
    transcriptionData = null;

    // Reset UI
    searchSection.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    uploadZone.style.display = '';
    progressContainer.classList.add('hidden');
    fileInput.value = '';
    searchInput.value = '';
    resultsList.innerHTML = '';
    resultsContainer.classList.add('hidden');
    noResults.classList.add('hidden');
    transcriptContent.classList.add('hidden');
    transcriptBtn.classList.remove('open');
    transcriptBtn.querySelector('span').textContent = 'Show Full Transcript';
    videoPlayer.src = '';
    progressFill.style.width = '0%';
});
