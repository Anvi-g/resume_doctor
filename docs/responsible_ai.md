# Responsible AI & Data Privacy Architecture

## Executive Overview
**Resume Doctor** incorporates Responsible AI by design to protect candidate privacy and eliminate algorithmic bias during resume analysis. This document outlines the architectural standards, privacy protections, and ethical guidelines implemented across the platform in accordance with the Microsoft Responsible AI Standard.

---

## 1. PII Redaction & Data Minimization (Module 2)
To comply with global data protection regulations (GDPR, CCPA) and minimize exposure of Personally Identifiable Information (PII):

- **Zero PII Exposure to Downstream LLMs**: Raw resumes containing candidate names, email addresses, phone numbers, home addresses, and government identification numbers (e.g., SSN) are never passed directly to generative AI models (Module 3 - GPT-4o).
- **Reverse-Offset Slicing Algorithm**: Entities detected by Azure AI Language are replaced from back-to-front by descending character offsets. This guarantees that replacement tags (e.g., `[NAME]`, `[EMAIL]`, `[PHONE]`, `[ADDRESS]`, `[SSN]`) do not alter earlier character indices.
- **Fail-Safe Offline Mode**: If external cloud endpoints are unreachable, an offline regex fallback ensures personal identifiers are sanitized before any processing occurs.

---

## 2. Fairness & Demographic Bias Mitigation
Traditional resume screening algorithms frequently perpetuate demographic, racial, gender, and socio-economic biases present in historical training data:

1. **Blind Scoring**: By replacing full names, contact info, and addresses with generic tokens, the ATS evaluation engine evaluates candidates purely on demonstrable competencies, work achievements, and measurable business impact.
2. **Neutral Keyword Matching**: Skill extraction relies on Named Entity Recognition (NER) calibrated against domain-specific technical skills, preventing favoritism based on educational prestige, geographic locations, or graduation years.
3. **Equitable STAR Bullet Rewrites**: Generative rewrites focus strictly on the STAR methodology (Situation, Task, Action, Result) with quantified metrics, regardless of candidate background.

---

## 3. Data Protection & Confidentiality
- **In-Transit Encryption**: All communication between the client, FastAPI gateway, and Azure AI-103 endpoints is encrypted using TLS 1.3.
- **No Data Retention for Model Training**: Enterprise Azure OpenAI and Azure AI Language services guarantee that customer data submitted through the API is not used to train, retrain, or improve any foundational AI models.
- **Stateless Analysis**: Uploaded resume files and extracted text are processed in memory and are discarded after analysis without persistent database storage.

---

## 4. Transparency & Human-in-the-Loop Oversight
- **Candidate Control**: The frontend interface provides a split comparison card allowing candidates to view the raw resume alongside the sanitized version with all detected PII badges.
- **Deterministic Recommendations**: Every score deduction or bullet critique is accompanied by actionable explanations, ensuring complete transparency into how recommendations were formulated.
- **Human Recruiter Authority**: Resume Doctor serves strictly as a decision-support copilot; final interview and hiring decisions remain solely with human recruiters and hiring managers.
