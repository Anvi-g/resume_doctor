"""
Module 4: Job Description (JD) Skill Gap Analyzer & Matcher
Responsible for:
1. TF-IDF vectorization and Cosine Similarity calculation between resume and JD.
2. Skill extraction from Job Descriptions using domain skill taxonomy and NER cues.
3. Skill gap analysis: identifying matched vs missing skills.
4. Calibrated hybrid percentage matching (Text Similarity + Skill Coverage).
5. Generating actionable recommendations to bridge the candidate's skill gaps.
"""

import re
import logging
from typing import List, Tuple, Set, Optional, Dict, Any
from collections import Counter
import math

from src.backend.models.schemas import JDMatchResult

logger = logging.getLogger(__name__)

# Try importing scikit-learn for TF-IDF and Cosine Similarity
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn is not installed. Using pure-Python TF-IDF fallback.")


# =====================================================================
# Comprehensive Technical & Professional Skill Taxonomy
# =====================================================================
SKILL_TAXONOMY: Set[str] = {
    # Programming Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "c", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "sql", "bash", "shell",

    # Web & Backend Frameworks
    "fastapi", "flask", "django", "express", "express.js", "node.js", "nodejs",
    "react", "react.js", "angular", "vue", "vue.js", "next.js", "nextjs", "svelte",
    "spring", "spring boot", "asp.net", "dotnet", ".net", "graphql", "rest api", "restful api",

    # Cloud & Infrastructure
    "azure", "aws", "amazon web services", "gcp", "google cloud", "docker", "kubernetes",
    "k8s", "terraform", "ansible", "ci/cd", "github actions", "gitlab ci", "jenkins",
    "helm", "prometheus", "grafana", "nginx", "linux", "cloudformation",

    # AI, ML & Data Science
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "llm", "large language models", "generative ai", "genai",
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
    "scipy", "langchain", "llamaindex", "hugging face", "openai", "azure openai",
    "vector database", "faiss", "pinecone", "chromadb", "rag",

    # Databases & Storage
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "sqlite", "cassandra", "dynamodb", "cosmosdb", "neo4j", "oracle", "snowflake",

    # Methodologies & Tools
    "git", "github", "gitlab", "jira", "agile", "scrum", "kanban", "devops",
    "microservices", "unit testing", "pytest", "test driven development", "tdd",
    "system design", "distributed systems", "kafka", "rabbitmq"
}


# Stopwords for text sanitization
COMMON_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

SKILL_ALIASES: Dict[str, str] = {
    "k8s": "kubernetes",
    "kubernetes": "k8s",
    "golang": "go",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node.js": "nodejs",
    "postgres": "postgresql",
    "postgresql": "postgres",
    "ts": "typescript",
    "js": "javascript",
    "py": "python"
}


class JDMatcherService:
    """
    Member 4 Service: Job Description Analyzer & Skill Gap Matcher.
    Combines TF-IDF Cosine Similarity with Set-Theoretic Skill Gap Analysis.
    """

    def __init__(self):
        self.use_sklearn = SKLEARN_AVAILABLE
        if self.use_sklearn:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 1),
                stop_words="english",
                token_pattern=r"(?u)\b[\w\-\+#\.]+\b",
                lowercase=True
            )
        else:
            self.vectorizer = None

    def clean_text(self, text: str) -> str:
        """Sanitizes text, standardizing whitespace and punctuation."""
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s\+\#\-\.]", " ", text)
        return " ".join(cleaned.split())

    def compute_tfidf_cosine_similarity(self, resume_text: str, jd_text: str) -> float:
        """
        Computes cosine similarity between TF-IDF representations of resume and JD.
        Returns a float between 0.0 and 1.0.
        """
        clean_resume = self.clean_text(resume_text)
        clean_jd = self.clean_text(jd_text)

        if not clean_resume.strip() or not clean_jd.strip():
            return 0.0

        if self.use_sklearn:
            try:
                tfidf_matrix = self.vectorizer.fit_transform([clean_resume, clean_jd])
                sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
                return float(sim_matrix[0][0])
            except Exception as e:
                logger.warning(f"sklearn TF-IDF error: {e}. Using pure-python fallback.")

        return self._pure_python_cosine_similarity(clean_resume, clean_jd)

    def _pure_python_cosine_similarity(self, text1: str, text2: str) -> float:
        """Pure-Python TF-IDF and Cosine Similarity fallback."""
        def tokenize(text: str) -> List[str]:
            words = re.findall(r"\b[\w\+\#\.-]+\b", text.lower())
            return [w for w in words if w not in COMMON_STOPWORDS and len(w) > 1]

        tokens1 = tokenize(text1)
        tokens2 = tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        tf1 = Counter(tokens1)
        tf2 = Counter(tokens2)
        all_terms = set(tf1.keys()).union(set(tf2.keys()))

        N = 2
        vec1, vec2 = [], []
        for term in all_terms:
            df = (1 if term in tf1 else 0) + (1 if term in tf2 else 0)
            idf = math.log((N + 1) / (df + 1)) + 1
            vec1.append(tf1.get(term, 0) * idf)
            vec2.append(tf2.get(term, 0) * idf)

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return min(1.0, max(0.0, dot / (norm1 * norm2)))

    def extract_jd_skills(self, jd_text: str) -> List[str]:
        """
        Extracts required technical skills from the Job Description text.
        Matches against taxonomy and canonicalizes casing.
        """
        if not jd_text or not jd_text.strip():
            return []

        lower_jd = jd_text.lower()
        extracted: Set[str] = set()

        for skill in SKILL_TAXONOMY:
            pattern = rf"(?<![\w\+\#]){re.escape(skill)}(?![\w\+\#])"
            if re.search(pattern, lower_jd):
                extracted.add(self._canonicalize_skill_name(skill))

        explicit_patterns = [
            r"(?:proficien(?:t|cy)\s+(?:in|with)|experience\s+(?:in|with)|knowledge\s+of|skills?:\s*)([A-Za-z0-9\+\#\.\,\s]{3,50})",
            r"(?:requirements?|qualifications?):\s*([A-Za-z0-9\+\#\.\,\s]{3,60})"
        ]
        for pat in explicit_patterns:
            matches = re.finditer(pat, jd_text, re.IGNORECASE)
            for m in matches:
                chunk = m.group(1)
                tokens = [t.strip().lower() for t in re.split(r"[\,\;\/\|]", chunk) if t.strip()]
                for tok in tokens:
                    if tok in SKILL_TAXONOMY:
                        extracted.add(self._canonicalize_skill_name(tok))

        return sorted(list(extracted))

    def _canonicalize_skill_name(self, skill: str) -> str:
        """Canonical casing for common technical skills."""
        casing_map = {
            "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
            "java": "Java", "c++": "C++", "c#": "C#", "sql": "SQL", "fastapi": "FastAPI",
            "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
            "azure": "Azure", "aws": "AWS", "gcp": "GCP", "git": "Git",
            "github actions": "GitHub Actions", "ci/cd": "CI/CD", "rest api": "REST API",
            "graphql": "GraphQL", "nlp": "NLP", "llm": "LLM", "machine learning": "Machine Learning",
            "deep learning": "Deep Learning", "pytorch": "PyTorch", "tensorflow": "TensorFlow",
            "postgresql": "PostgreSQL", "mongodb": "MongoDB", "redis": "Redis",
            "scikit-learn": "Scikit-Learn", "pandas": "Pandas", "numpy": "NumPy",
            "react": "React", "next.js": "Next.js", "node.js": "Node.js", "linux": "Linux"
        }
        return casing_map.get(skill.lower(), skill.title())

    def analyze_skill_gap(
        self, 
        resume_skills: List[str], 
        jd_skills: List[str]
    ) -> Tuple[List[str], List[str], float]:
        """
        Compares resume skills with JD skills using exact canonical matching and alias resolution.
        Avoids false substring matches (e.g. 'sql' will not match 'postgresql').
        """
        resume_set_lower = {s.strip().lower() for s in resume_skills if s.strip()}
        
        matched: List[str] = []
        missing: List[str] = []

        for jd_skill in jd_skills:
            skill_lower = jd_skill.lower()
            is_matched = (
                skill_lower in resume_set_lower
                or SKILL_ALIASES.get(skill_lower) in resume_set_lower
                or any(SKILL_ALIASES.get(r) == skill_lower for r in resume_set_lower)
            )
            if is_matched:
                matched.append(jd_skill)
            else:
                missing.append(jd_skill)

        if jd_skills:
            ratio = len(matched) / len(jd_skills)
        else:
            ratio = 1.0 if resume_skills else 0.5

        return sorted(matched), sorted(missing), min(1.0, max(0.0, ratio))

    def generate_recommendations(
        self, 
        missing_skills: List[str], 
        match_percentage: float, 
        cosine_sim: float
    ) -> List[str]:
        """Generates targeted, actionable advice for the candidate to increase score."""
        recs: List[str] = []

        if missing_skills:
            top_missing = missing_skills[:4]
            recs.append(
                f"Add evidence of experience with high-priority missing skills: {', '.join(top_missing)}."
            )
            recs.append(
                f"Integrate keywords '{top_missing[0]}' into your project description bullet points with measurable outcomes."
            )

        if cosine_sim < 0.15:
            recs.append(
                "Align your resume summary and job titles closer to the terminology used in the Job Description."
            )
        elif cosine_sim >= 0.25:
            recs.append(
                "Strong semantic alignment with Job Description. Ensure your achievements quantify impact (e.g., % latency reduced, $ saved)."
            )

        if match_percentage < 50.0:
            recs.append(
                "Significant skill gap detected. Consider highlighting transferable skills and relevant coursework/certifications."
            )
        elif match_percentage >= 80.0:
            recs.append(
                "High match! Tailor your recent project bullets using the STAR method to maximize interview callbacks."
            )
        else:
            recs.append(
                "Good foundation. Address the missing skills in a technical skills section to push your match above 80%."
            )

        return recs

    def match(self, clean_text: str, jd_text: str, resume_skills: List[str]) -> JDMatchResult:
        """
        Synchronous core matching method.
        Calculates:
        1. Cosine similarity via TF-IDF
        2. Skill match ratio
        3. Calibrated overall match percentage (0.0 to 100.0%)
        """
        if not jd_text or not jd_text.strip():
            return JDMatchResult(
                match_percentage=0.0,
                matched_skills=[],
                missing_skills=[],
                recommendations=["Please provide a Job Description to calculate skill match percentage."],
                cosine_similarity=0.0,
                skill_match_ratio=0.0
            )

        # 1. Cosine Similarity (0.0 - 1.0)
        cosine_sim = self.compute_tfidf_cosine_similarity(clean_text, jd_text)

        # 2. Extract skills from JD
        jd_skills = self.extract_jd_skills(jd_text)

        combined_resume_skills = set(resume_skills)
        if len(combined_resume_skills) < 3:
            extracted_from_resume = self.extract_jd_skills(clean_text)
            combined_resume_skills.update(extracted_from_resume)

        # 3. Analyze Skill Gap
        matched_skills, missing_skills, skill_ratio = self.analyze_skill_gap(
            list(combined_resume_skills), 
            jd_skills
        )

        # 4. Calibrated Hybrid Score:
        # In document-level NLP, cosine similarity between different writing styles
        # peaks around 0.35-0.45. We calibrate raw cosine by scaling it realistically.
        normalized_cosine = min(1.0, max(0.0, cosine_sim * 2.5))

        if jd_skills:
            # 35% Calibrated Semantic Overlap + 65% Skill Coverage
            hybrid_score = (0.35 * normalized_cosine + 0.65 * skill_ratio) * 100.0
        else:
            hybrid_score = normalized_cosine * 100.0

        match_percentage = round(min(100.0, max(0.0, hybrid_score)), 1)
        recommendations = self.generate_recommendations(missing_skills, match_percentage, cosine_sim)

        return JDMatchResult(
            match_percentage=match_percentage,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            recommendations=recommendations,
            cosine_similarity=round(cosine_sim, 3),
            skill_match_ratio=round(skill_ratio, 3)
        )

    def compute_jd_match(self, resume_text: str, target_jd: str) -> Dict[str, Any]:
        """
        Legacy dictionary interface for backward compatibility with teammate modules.
        """
        result = self.match(resume_text, target_jd, [])
        return {
            "match_score": result.match_percentage,
            "matching_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
            "recommendations": result.recommendations,
            "status": "success",
        }


# =====================================================================
# Standalone Async Function Contract Required by Master Plan
# =====================================================================
_matcher_instance = JDMatcherService()

async def match_jd_with_resume(
    clean_text: str, 
    jd_text: str, 
    resume_skills: List[str]
) -> JDMatchResult:
    """
    Exact function contract specified for Member 4:
    async def match_jd_with_resume(clean_text: str, jd_text: str, resume_skills: list[str]) -> JDMatchResult
    """
    return _matcher_instance.match(clean_text, jd_text, resume_skills)
