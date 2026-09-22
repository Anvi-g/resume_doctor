const API_URL = 'http://localhost:8000/api/analyze';
const HEALTH_URL = 'http://localhost:8000/api/health';
const form = document.querySelector('#analysis-form');
const fileInput = document.querySelector('#resume-file');
const dropZone = document.querySelector('#drop-zone');
const fileLabel = document.querySelector('#file-label');
const fileMeta = document.querySelector('#file-meta');
const button = document.querySelector('#analyze-button');
const errorMessage = document.querySelector('#form-error');
const results = document.querySelector('#results');
const statusBadge = document.querySelector('#status-badge');

async function updateBackendStatus() {
  if (!statusBadge) return;
  try {
    const res = await fetch(HEALTH_URL);
    if (!res.ok) return;
    const data = await res.json();
    const mode = data.agentic?.mode;
    if (mode === 'agent_service') {
      statusBadge.innerHTML = '<span class="status-dot"></span> AZURE AI FOUNDRY';
    } else if (mode === 'responses') {
      statusBadge.innerHTML = '<span class="status-dot"></span> AZURE OPENAI RESPONSES';
    } else {
      statusBadge.innerHTML = '<span class="status-dot"></span> LOCAL WORKSPACE';
    }
  } catch (e) {
    // Keep default static text if server is offline
  }
}
updateBackendStatus();

function chooseFile(file) {
  if (!file) return;
  fileLabel.textContent = file.name;
  fileMeta.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB ready for analysis`;
}

fileInput.addEventListener('change', () => chooseFile(fileInput.files[0]));
['dragenter', 'dragover'].forEach(eventName => dropZone.addEventListener(eventName, event => {
  event.preventDefault();
  dropZone.classList.add('dragging');
}));
['dragleave', 'drop'].forEach(eventName => dropZone.addEventListener(eventName, event => {
  event.preventDefault();
  dropZone.classList.remove('dragging');
}));
dropZone.addEventListener('drop', event => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  chooseFile(file);
});

function list(items, fallback) {
  if (!Array.isArray(items) || items.length === 0) return `<p>${fallback}</p>`;
  return `<ul>${items.map(item => `<li>${escapeHtml(String(item))}</li>`).join('')}</ul>`;
}

function escapeHtml(value) {
  return value.replace(/[&<>\"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', "'": '&#039;' }[character]));
}

function diffWords(original, rewritten) {
  const normalize = word => String(word).toLowerCase().replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, '');
  const segments = text => String(text).split(/\s+/).filter(Boolean);
  const counts = {};
  segments(original).forEach(word => {
    const key = normalize(word);
    if (key) counts[key] = (counts[key] || 0) + 1;
  });
  return segments(rewritten).map(word => {
    const key = normalize(word);
    if (key && (counts[key] || 0) > 0) {
      counts[key]--;
      return escapeHtml(word);
    }
    return `<mark>${escapeHtml(word)}</mark>`;
  }).join(' ');
}

function renderRewrites(data) {
  const raw = data.star_bullet_rewrites || {};
  const rewrites = Array.isArray(raw) ? raw : (raw.rewrites || []);
  if (!Array.isArray(rewrites) || rewrites.length === 0) {
    return `<div class="result-block"><h3>Rewritten sentences</h3><p>No bullets were rewritten for this resume.</p></div>`;
  }
  const items = rewrites.map(rewrite => {
    const improved = rewrite.rewritten_bullet || rewrite.improved_star || '';
    const original = rewrite.original_bullet || rewrite.original || '';
    return `
      <div class="rewrite-item">
        <div class="rewrite-pair"><span class="rewrite-label">Original</span><p>${escapeHtml(original)}</p></div>
        <div class="rewrite-arrow" aria-hidden="true">&darr;</div>
        <div class="rewrite-pair"><span class="rewrite-label">Rewritten (STAR)</span><p>${diffWords(original, improved)}</p></div>
      </div>`;
  }).join('');
  return `<div class="result-block"><h3>Rewritten sentences</h3>${items}</div>`;
}

function renderResults(data) {
  const ats = data.ats_analysis || {};
  const match = data.jd_match || {};
  const doc = data.doc_summary || {};
  const pii = data.pii_summary || {};
  const score = ats.ats_score ?? ats.overall_score ?? 0;
  const strengths = ats.strengths || [];
  const weaknesses = ats.weaknesses || ats.improvements || [];
  const matched = match.matched_skills || [];
  const missing = match.missing_skills || [];

  results.innerHTML = `
    <div class="result-head"><div><span class="eyebrow">ANALYSIS COMPLETE</span><h2>Resume readout</h2></div><div class="score">${Math.round(score)}<small>/100 ATS</small></div></div>
    <div class="result-block"><h3>Role alignment</h3><div class="metric-grid"><div class="metric"><strong>${Math.round(match.match_percentage || 0)}%</strong><span>match score</span></div><div class="metric"><strong>${matched.length}</strong><span>matched skills</span></div></div></div>
    <div class="result-block"><h3>What is working</h3>${list(strengths, 'No strengths were returned.')}</div>
    <div class="result-block"><h3>Next improvements</h3>${list(weaknesses.length ? weaknesses : missing, 'No immediate gaps were returned.')}</div>
    <div class="result-block"><h3>Extraction</h3><p>${doc.page_count || 1} page${(doc.page_count || 1) === 1 ? '' : 's'} parsed · ${Array.isArray(pii.detected_pii) ? pii.detected_pii.length : 0} sensitive entities detected</p></div>
    ${renderRewrites(data)}`;
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  errorMessage.textContent = '';
  const file = fileInput.files[0];
  if (!file) {
    errorMessage.textContent = 'Please choose a PDF, DOCX, or TXT resume.';
    return;
  }
  const payload = new FormData();
  payload.append('resume_file', file);
  payload.append('job_description', document.querySelector('#job-description').value);
  payload.append('target_role', document.querySelector('#target-role').value);
  button.disabled = true;
  button.querySelector('span').textContent = 'Analyzing...';
  try {
    const response = await fetch(API_URL, { method: 'POST', body: payload });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The analysis request failed.');
    renderResults(data);
  } catch (error) {
    errorMessage.textContent = `${error.message} Is the backend running on port 8000?`;
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Analyze resume';
  }
});
