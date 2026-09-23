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

const SAMPLE_JDS = {
  azure_dev: `Senior Cloud Engineer / Python Developer
Requirements:
- 5+ years of experience with Python, FastAPI, and RESTful APIs.
- Extensive expertise in Cloud Services (OpenAI, AI Language, Document Intelligence, App Service).
- Hands-on experience with Docker, Kubernetes, CI/CD pipelines, and PostgreSQL.
- Strong knowledge of Microservices Architecture, Unit Testing (pytest), and System Design.
- Cloud Certifications preferred.`,

  data_engineer: `Lead AI / ML Data Engineer
Requirements:
- Strong proficiency in Python, PyTorch, TensorFlow, Scikit-Learn, and NLP techniques.
- Experience building RAG pipelines using OpenAI, LangChain, and Vector Databases (Pinecone/Chroma).
- Knowledge of Data Pipelines, SQL, PostgreSQL, Linux, Git, and Docker.
- Experience with PII redaction and Responsible AI compliance standards.`
};

async function updateBackendStatus() {
  if (!statusBadge) return;
  try {
    const res = await fetch(HEALTH_URL);
    if (!res.ok) {
      statusBadge.innerHTML = '<span class="status-dot offline"></span> BACKEND DISCONNECTED';
      return;
    }
    const data = await res.json();
    const mode = data.agentic?.mode;
    const isMock = data.modules?.m3_openai_ats === 'Mock';

    if (mode === 'agent_service') {
      statusBadge.innerHTML = '<span class="status-dot live"></span> AZURE AI FOUNDRY (AGENT SERVICE)';
    } else if (mode === 'responses') {
      statusBadge.innerHTML = '<span class="status-dot live"></span> AZURE OPENAI (RESPONSES)';
    } else if (data.agentic?.configured && !isMock) {
      statusBadge.innerHTML = '<span class="status-dot live"></span> AZURE AI CONNECTED';
    } else {
      statusBadge.innerHTML = '<span class="status-dot offline"></span> OFFLINE FALLBACK MODE';
    }
  } catch (e) {
    statusBadge.innerHTML = '<span class="status-dot offline"></span> BACKEND DISCONNECTED';
  }
}
updateBackendStatus();

const cloudBtn = document.querySelector('#btn-cloud-jd');
const aimlBtn = document.querySelector('#btn-aiml-jd');
const jdTextArea = document.querySelector('#job-description');

if (cloudBtn && jdTextArea) {
  cloudBtn.addEventListener('click', () => {
    jdTextArea.value = SAMPLE_JDS.azure_dev;
  });
}
if (aimlBtn && jdTextArea) {
  aimlBtn.addEventListener('click', () => {
    jdTextArea.value = SAMPLE_JDS.data_engineer;
  });
}

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

let currentPiiMode = 'true';

function renderPiiEntities(detectedPii, isRedacted) {
  if (!Array.isArray(detectedPii) || detectedPii.length === 0) {
    return `<div class="pii-entities-container"><span class="pii-empty">No sensitive entities detected</span></div>`;
  }
  const validPii = detectedPii.filter(item => item && item.type && item.type !== 'PII Masking');
  if (validPii.length === 0) {
    return `<div class="pii-entities-container"><span class="pii-empty">No sensitive entities detected</span></div>`;
  }

  const itemsHtml = validPii.slice(0, 12).map(ent => {
    const typeLabel = escapeHtml(String(ent.type || 'PII'));
    const rawText = escapeHtml(String(ent.text || '***'));
    if (isRedacted) {
      return `<span class="pii-pill redacted"><strong class="pii-type">🔒 ${typeLabel}:</strong> [REDACTED]</span>`;
    } else {
      return `<span class="pii-pill raw"><strong class="pii-type">⚪ ${typeLabel}:</strong> ${rawText}</span>`;
    }
  }).join('');

  const moreCount = validPii.length > 12 ? `<span class="pii-pill more">+${validPii.length - 12} more</span>` : '';
  return `<div class="pii-entities-container">${itemsHtml}${moreCount}</div>`;
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
  const detectedPii = pii.detected_pii || [];

  const piiCount = Array.isArray(detectedPii) ? detectedPii.filter(item => item && item.type && item.type !== 'PII Masking').length : 0;
  
  const getPiiLabel = (mode) => {
    if (mode === 'false') {
      return `⚪ PII Masking Disabled (${piiCount} sensitive entities visible)`;
    }
    return piiCount > 0 
      ? `🟢 ${piiCount} sensitive entities redacted` 
      : '🟢 0 PII entities detected';
  };

  const matchedPills = matched.length > 0
    ? matched.map(s => `<span class="skill-pill matched">✓ ${escapeHtml(String(s))}</span>`).join('')
    : '<span class="no-skills">No matched skills detected</span>';

  const missingPills = missing.length > 0
    ? missing.map(s => `<span class="skill-pill missing">✕ ${escapeHtml(String(s))}</span>`).join('')
    : '<span class="no-skills">No skill gaps identified</span>';

  results.innerHTML = `
    <div class="result-head"><div><span class="eyebrow">ANALYSIS COMPLETE</span><h2>Resume readout</h2></div><div class="score">${Math.round(score)}<small>/100 ATS</small></div></div>
    
    <div class="result-block">
      <h3>Role alignment</h3>
      <div class="metric-grid">
        <div class="metric"><strong>${Math.round(match.match_percentage || 0)}%</strong><span>match score</span></div>
        <div class="metric"><strong>${matched.length}</strong><span>matched skills</span></div>
      </div>
      <div class="skills-breakdown">
        <div class="skill-group">
          <span class="skill-group-label">Matched Skills (${matched.length})</span>
          <div class="skill-pills-container">${matchedPills}</div>
        </div>
        <div class="skill-group">
          <span class="skill-group-label">Missing Skills / Skill Gaps (${missing.length})</span>
          <div class="skill-pills-container">${missingPills}</div>
        </div>
      </div>
    </div>

    <div class="result-block"><h3>What is working</h3>${list(strengths, 'No strengths were returned.')}</div>
    <div class="result-block"><h3>Next improvements</h3>${list(weaknesses.length ? weaknesses : missing, 'No immediate gaps were returned.')}</div>
    
    <div class="result-block">
      <div class="pii-dropdown-header">
        <h3>Extraction</h3>
        <div class="pii-select-wrapper">
          <label for="pii-select" class="pii-select-label">PII Redaction:</label>
          <select id="pii-select" class="pii-select">
            <option value="true" ${currentPiiMode === 'true' ? 'selected' : ''}>🟢 Redact PII (Active)</option>
            <option value="false" ${currentPiiMode === 'false' ? 'selected' : ''}>⚪ Show Raw (Disabled)</option>
          </select>
        </div>
      </div>
      <p>${doc.page_count || 1} page${(doc.page_count || 1) === 1 ? '' : 's'} parsed · <span id="pii-status-span">${getPiiLabel(currentPiiMode)}</span></p>
      <div id="pii-entities-wrapper">${renderPiiEntities(detectedPii, currentPiiMode === 'true')}</div>
    </div>
    
    ${renderRewrites(data)}`;

  const piiSelect = document.querySelector('#pii-select');
  const piiStatusSpan = document.querySelector('#pii-status-span');
  const piiEntitiesWrapper = document.querySelector('#pii-entities-wrapper');
  if (piiSelect && piiStatusSpan && piiEntitiesWrapper) {
    piiSelect.addEventListener('change', (e) => {
      currentPiiMode = e.target.value;
      const isRedacted = currentPiiMode === 'true';
      piiStatusSpan.textContent = getPiiLabel(currentPiiMode);
      piiEntitiesWrapper.innerHTML = renderPiiEntities(detectedPii, isRedacted);
    });
  }
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
  payload.append('enable_pii', currentPiiMode);

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
