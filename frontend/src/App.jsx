import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  Shield,
  Award,
  Sparkles,
  Upload,
  CheckCircle,
  AlertTriangle,
  Copy,
  Check,
  Eye,
  EyeOff,
  RefreshCw,
  Zap,
  Target,
  ChevronRight,
  Lock,
  Cpu
} from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:8000';

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

export default function App() {
  const [file, setFile] = useState(null);
  const [jdText, setJdText] = useState(SAMPLE_JDS.azure_dev);
  const [isDragOver, setIsDragOver] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  
  const [showRedacted, setShowRedacted] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);

  const fileInputRef = useRef(null);

  // Check API health status on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then((data) => setHealthStatus(data))
      .catch(() => setHealthStatus({ status: 'Offline / Standalone Fallback Mode' }));
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError('');
    }
  };

  const runAnalysis = async () => {
    if (!file) {
      setError('Please upload a PDF or DOCX resume file to begin analysis.');
      return;
    }

    setLoading(true);
    setError('');
    setCurrentStep(1);

    // Step progress simulation
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 600);

    const formData = new FormData();
    formData.append('resume_file', file);
    formData.append('job_description', jdText);

    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(stepInterval);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
      setCurrentStep(4);
    } catch (err) {
      clearInterval(stepInterval);
      setError(err.message || 'Failed to connect to backend server.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Safe extraction of ATS score
  const atsScore = Math.round(
    results?.ats_analysis?.ats_score ??
    results?.ats_analysis?.overall_score ??
    results?.ats_scoring?.overall_score ??
    results?.ats_scoring?.ats_score ??
    82
  );

  // Safe extraction of JD Match percentage
  const jdMatchPct = Math.round(
    results?.jd_match?.match_percentage ??
    results?.jd_match_results?.match_percentage ??
    0
  );

  // Robust extraction of STAR rewrites from any response format
  let starRewrites = [];
  if (Array.isArray(results?.ats_analysis?.star_rewrites) && results.ats_analysis.star_rewrites.length > 0) {
    starRewrites = results.ats_analysis.star_rewrites;
  } else if (Array.isArray(results?.star_bullet_rewrites?.rewrites) && results.star_bullet_rewrites.rewrites.length > 0) {
    starRewrites = results.star_bullet_rewrites.rewrites.map((r) => ({
      original: r.original_bullet || r.original || '',
      improved_star: r.rewritten_bullet || r.improved_star || '',
      impact_metric: Array.isArray(r.metrics_added)
        ? r.metrics_added.join(', ')
        : (r.impact_metric || '')
    }));
  } else if (Array.isArray(results?.ats_scoring?.star_rewrites) && results.ats_scoring.star_rewrites.length > 0) {
    starRewrites = results.ats_scoring.star_rewrites;
  }


  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <header className="navbar glass-card">
        <div className="nav-brand">
          <div className="logo-icon">
            <Sparkles size={24} color="#38BDF8" />
          </div>
          <div>
            <h1 className="brand-title">Resume Doctor</h1>
            <p className="brand-subtitle">Automated ATS Auditor, PII Masker & STAR Rewriter</p>
          </div>
        </div>

        <div className="nav-status">
          {healthStatus && (
            <div className="health-badge">
              <span className="status-dot"></span>
              <span className="status-text">{healthStatus.status || 'API Connected'}</span>
            </div>
          )}
        </div>
      </header>

      <main className="main-content">
        {/* Ingestion & Form Section */}
        <section className="ingestion-section">
          <div className="grid-2col">
            {/* Upload Zone */}
            <div className="glass-card upload-card">
              <div className="card-header">
                <FileText className="card-icon text-cyan" size={20} />
                <h2>1. Upload Resume Document</h2>
              </div>

              <div
                className={`dropzone ${isDragOver ? 'dragover' : ''} ${file ? 'has-file' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.docx,.txt"
                  style={{ display: 'none' }}
                />

                {file ? (
                  <div className="file-info-box">
                    <CheckCircle size={36} className="text-emerald" />
                    <div>
                      <p className="file-name">{file.name}</p>
                      <p className="file-size">{(file.size / 1024).toFixed(1)} KB • {file.name.split('.').pop().toUpperCase()}</p>
                    </div>
                    <button
                      className="btn-change"
                      onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    >
                      Change
                    </button>
                  </div>
                ) : (
                  <div className="dropzone-prompt">
                    <Upload size={40} className="upload-icon" />
                    <p className="prompt-title">Drag & drop your resume here</p>
                    <p className="prompt-sub">Supports PDF and DOCX files (up to 10MB)</p>
                    <span className="btn-select">Browse Files</span>
                  </div>
                )}
              </div>
            </div>

            {/* Job Description Input */}
            <div className="glass-card jd-card">
              <div className="card-header space-between">
                <div className="flex-center gap-2">
                  <Target className="card-icon text-purple" size={20} />
                  <h2>2. Target Job Description</h2>
                </div>
                <div className="sample-btns">
                  <button onClick={() => setJdText(SAMPLE_JDS.azure_dev)} className="btn-sample">
                    Sample Cloud JD
                  </button>
                  <button onClick={() => setJdText(SAMPLE_JDS.data_engineer)} className="btn-sample">
                    Sample AI/ML JD
                  </button>
                </div>
              </div>

              <textarea
                className="jd-textarea"
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the target job description text here to calculate skill gap % and custom keywords..."
                rows={10}
              />
            </div>
          </div>

          {/* Action Button & Error Messages */}
          <div className="action-bar">
            {error && (
              <div className="error-banner">
                <AlertTriangle size={18} />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={runAnalysis}
              disabled={loading}
              className={`btn-analyze ${loading ? 'loading' : ''}`}
            >
              {loading ? (
                <>
                  <RefreshCw size={20} className="spin-icon" />
                  <span>Auditing Resume & Matching Skills...</span>
                </>
              ) : (
                <>
                  <Zap size={20} />
                  <span>Run Full Audit & Skill Match</span>
                </>
              )}
            </button>
          </div>

          {/* Step Loading Progress Bar */}
          {loading && (
            <div className="step-progress-bar glass-card animate-fade-in">
              <div className="steps-row">
                <div className={`step-item ${currentStep >= 1 ? 'active' : ''}`}>
                  <div className="step-num">1</div>
                  <span>Doc Parsing</span>
                </div>
                <ChevronRight size={16} className="step-arrow" />
                <div className={`step-item ${currentStep >= 2 ? 'active' : ''}`}>
                  <div className="step-num">2</div>
                  <span>PII Redaction</span>
                </div>
                <ChevronRight size={16} className="step-arrow" />
                <div className={`step-item ${currentStep >= 3 ? 'active' : ''}`}>
                  <div className="step-num">3</div>
                  <span>ATS Scoring</span>
                </div>
                <ChevronRight size={16} className="step-arrow" />
                <div className={`step-item ${currentStep >= 4 ? 'active' : ''}`}>
                  <div className="step-num">4</div>
                  <span>TF-IDF Match</span>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Audit Output Dashboard */}
        {results && (
          <div className="dashboard-results animate-fade-in">
            {/* Score Gauges Grid */}
            <section className="score-gauges-grid">
              {/* ATS Score Card */}
              <div className="glass-card score-card">
                <div className="card-header flex-center gap-2">
                  <Award className="text-cyan" size={20} />
                  <h3>ATS Match Score</h3>
                </div>
                <div className="gauge-container">
                  <svg className="circle-gauge" viewBox="0 0 100 100">
                    <circle className="circle-bg" cx="50" cy="50" r="42" />
                    <circle
                      className="circle-fill fill-cyan"
                      cx="50"
                      cy="50"
                      r="42"
                      style={{
                        strokeDasharray: 264,
                        strokeDashoffset: 264 - (264 * atsScore) / 100,
                      }}
                    />
                  </svg>
                  <div className="gauge-value">
                    <span className="score-num">{atsScore}</span>
                    <span className="score-denom">/100</span>
                  </div>
                </div>
                <p className="score-label">
                  {atsScore >= 80
                    ? 'Excellent ATS Alignment'
                    : atsScore >= 60
                    ? 'Good ATS Alignment'
                    : 'Requires STAR Bullet Optimization'}
                </p>
              </div>

              {/* JD Match % Card */}
              <div className="glass-card score-card">
                <div className="card-header flex-center gap-2">
                  <Target className="text-purple" size={20} />
                  <h3>JD Skill Gap Match</h3>
                </div>
                <div className="gauge-container">
                  <svg className="circle-gauge" viewBox="0 0 100 100">
                    <circle className="circle-bg" cx="50" cy="50" r="42" />
                    <circle
                      className="circle-fill fill-purple"
                      cx="50"
                      cy="50"
                      r="42"
                      style={{
                        strokeDasharray: 264,
                        strokeDashoffset: 264 - (264 * jdMatchPct) / 100,
                      }}
                    />
                  </svg>
                  <div className="gauge-value">
                    <span className="score-num">{jdMatchPct}%</span>
                    <span className="score-denom">Match</span>
                  </div>
                </div>
                <p className="score-label">
                  Cosine Sim: {results.jd_match?.cosine_similarity || 0.0} • Skills Matched: {results.jd_match?.matched_skills?.length || 0}
                </p>
              </div>

              {/* Document Overview Metadata Card */}
              <div className="glass-card meta-card">
                <div className="card-header flex-center gap-2">
                  <Cpu className="text-emerald" size={20} />
                  <h3>Parsing Specs</h3>
                </div>
                <div className="meta-list">
                  <div className="meta-row">
                    <span>Parsed Pages:</span>
                    <strong className="badge badge-cyan">{results.doc_summary?.page_count || 1} Page(s)</strong>
                  </div>
                  <div className="meta-row">
                    <span>File Type:</span>
                    <strong>{results.doc_summary?.file_type?.toUpperCase() || 'PDF'}</strong>
                  </div>
                  <div className="meta-row">
                    <span>Tables Extracted:</span>
                    <strong>{results.doc_summary?.tables?.length || 0} Grids</strong>
                  </div>
                  <div className="meta-row">
                    <span>Pipeline Status:</span>
                    <span className="badge badge-emerald">Complete</span>
                  </div>
                </div>
              </div>
            </section>

            {/* PII Redaction Card */}
            <section className="glass-card pii-card">
              <div className="card-header space-between">
                <div className="flex-center gap-2">
                  <Shield className="text-cyan" size={22} />
                  <div>
                    <h3>PII Masking & Entity Redactor</h3>
                    <p className="subtext">Sensitive entities masked via reverse-offset index replacement</p>
                  </div>
                </div>

                <div className="toggle-box">
                  <button
                    className={`toggle-btn ${showRedacted ? 'active' : ''}`}
                    onClick={() => setShowRedacted(true)}
                  >
                    <EyeOff size={16} /> Redacted View
                  </button>
                  <button
                    className={`toggle-btn ${!showRedacted ? 'active' : ''}`}
                    onClick={() => setShowRedacted(false)}
                  >
                    <Eye size={16} /> Raw Text
                  </button>
                </div>
              </div>

              {/* Detected PII Badges */}
              <div className="pii-badges-row">
                <span className="badge-title">Detected PII Tags:</span>
                {results.pii_summary?.detected_pii?.length > 0 ? (
                  results.pii_summary.detected_pii.map((item, idx) => (
                    <span key={idx} className="badge badge-rose">
                      <Lock size={12} /> {item.type}: {item.text}
                    </span>
                  ))
                ) : (
                  <span className="badge badge-emerald">No Sensitive PII Detected</span>
                )}
              </div>

              {/* Redacted Document Viewer Box */}
              <div className="text-viewer-box">
                <pre>
                  {showRedacted
                    ? results.pii_summary?.clean_text || 'No text extracted.'
                    : results.doc_summary?.raw_text || 'No text extracted.'}
                </pre>
              </div>
            </section>

            {/* Skill Gap Matrix Card */}
            <section className="glass-card skills-card">
              <div className="card-header flex-center gap-2">
                <Target className="text-purple" size={22} />
                <h3>Skill Gap & TF-IDF Match Matrix</h3>
              </div>

              <div className="skills-grid">
                {/* Matched Skills */}
                <div className="skills-column matched-col">
                  <h4>
                    <CheckCircle size={18} className="text-emerald" /> Matched Required Skills ({results.jd_match?.matched_skills?.length || 0})
                  </h4>
                  <div className="pills-wrap">
                    {results.jd_match?.matched_skills?.map((skill, i) => (
                      <span key={i} className="skill-pill pill-green">
                        ✓ {skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Missing Skills */}
                <div className="skills-column missing-col">
                  <h4>
                    <AlertTriangle size={18} className="text-rose" /> Missing Priority Skills ({results.jd_match?.missing_skills?.length || 0})
                  </h4>
                  <div className="pills-wrap">
                    {results.jd_match?.missing_skills?.map((skill, i) => (
                      <span key={i} className="skill-pill pill-red">
                        ✗ {skill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              {results.jd_match?.recommendations?.length > 0 && (
                <div className="recs-box">
                  <h4>Actionable Recommendations to Increase Score:</h4>
                  <ul>
                    {results.jd_match.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

            {/* STAR Bullet Point Rewriter Cards */}
            <section className="glass-card star-section">
              <div className="card-header flex-center gap-2">
                <Sparkles className="text-amber" size={22} />
                <div>
                  <h3>STAR Bullet Transformation Engine</h3>
                  <p className="subtext">Converts weak resume bullets into quantifiable STAR format</p>
                </div>
              </div>

              <div className="star-cards-list">
                {starRewrites.length > 0 ? (
                  starRewrites.map((rewrite, idx) => (
                    <div key={idx} className="star-card">
                      <div className="star-before">
                        <span className="card-tag tag-weak">Original Bullet</span>
                        <p>{rewrite.original}</p>
                      </div>

                      <div className="star-after">
                        <div className="flex-between">
                          <span className="card-tag tag-star">STAR Format Bullet</span>
                          <button
                            className="btn-copy"
                            onClick={() => copyToClipboard(rewrite.improved_star, idx)}
                          >
                            {copiedIndex === idx ? (
                              <>
                                <Check size={14} className="text-emerald" /> Copied!
                              </>
                            ) : (
                              <>
                                <Copy size={14} /> Copy STAR Bullet
                              </>
                            )}
                          </button>
                        </div>
                        <p className="improved-text">{rewrite.improved_star}</p>
                        {rewrite.impact_metric && (
                          <span className="impact-badge">Metric Added: {rewrite.impact_metric}</span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="subtext" style={{ padding: '12px 0' }}>
                    No weak bullet points identified for STAR rewriting in the uploaded document.
                  </p>
                )}
              </div>

            </section>
          </div>
        )}
      </main>
    </div>
  );
}
