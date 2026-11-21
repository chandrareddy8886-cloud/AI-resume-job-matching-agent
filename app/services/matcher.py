import re
from typing import List, Dict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SKILL_ALIASES = {
    "python": ["python"],
    "sql": ["sql", "mysql", "postgresql", "postgres"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django"],
    "rest api": ["rest api", "restful api"],
    "git": ["git", "github"],
    "docker": ["docker", "containerization", "containers"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services", "ec2", "s3", "rds"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "pyspark": ["pyspark", "spark"],
    "machine learning": ["machine learning", "ml"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "llm": ["llm", "large language model", "generative ai"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "openai api": ["openai api"],
    "pytest": ["pytest"],
    "selenium": ["selenium"],
    "playwright": ["playwright"],
    "linux": ["linux"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration", "continuous delivery"],
    "customer service": ["customer service", "customer care", "client service", "customer satisfaction"],
    "customer support": ["customer support", "client support", "customer assistance"],
    "technical support": ["technical support", "product support", "it support", "help desk", "helpdesk", "service desk"],
    "troubleshooting": ["troubleshooting", "troubleshoot", "diagnose issues", "issue diagnosis", "problem diagnosis"],
    "problem solving": ["problem solving", "problem-solving", "root cause analysis", "root-cause analysis"],
    "communication": ["communication skills", "verbal communication", "written communication", "interpersonal skills"],
    "documentation": ["documentation", "documenting", "technical documentation", "knowledge base", "self-help documents"],
    "issue escalation": ["escalation", "escalate", "escalating issues"],
    "incident management": ["incident management", "incident resolution", "incident handling"],
    "ticketing systems": ["ticketing system", "ticketing tools", "service now", "servicenow", "jira service management"],
    "call handling": ["call handling", "call logs", "email support", "phone support", "inbound calls"],
    "crm": ["crm", "customer relationship management", "salesforce"],
    "sla": ["sla", "service level agreement", "service level agreements"],
    "time management": ["time management", "prioritization", "prioritisation"],
    "active listening": ["active listening", "listening skills"],
    "teamwork": ["teamwork", "team player", "cross-functional collaboration"],
    "data analysis": ["data analysis", "data analytics", "analyze data", "analyse data"],
    "excel": ["excel", "microsoft excel", "spreadsheets"],
    "networking": ["networking", "tcp/ip", "dns", "dhcp"],
    "windows": ["windows", "windows 10", "windows 11"],
    "cybersecurity": ["cybersecurity", "information security", "security best practices"],
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold())


def extract_skills(text: str) -> List[str]:
    normalized = _normalise(text)
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)"
            if re.search(pattern, normalized):
                found.append(canonical)
                break
    return sorted(set(found))


def retrieve_relevant_resume_sentences(resume_text: str, job_description: str, top_k: int = 5):
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", resume_text)
        if len(sentence.strip()) > 15
    ]
    if not sentences:
        return []
    corpus = sentences + [job_description]
    matrix = TfidfVectorizer(stop_words="english").fit_transform(corpus)
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(zip(sentences, scores), key=lambda item: item[1], reverse=True)
    return [{"text": sentence, "score": round(float(score), 4)} for sentence, score in ranked[:top_k]]


def match_resume_to_job(resume_text: str, job_description: str) -> Dict:
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty.")
    if not job_description or not job_description.strip():
        raise ValueError("Job description is empty.")

    resume_skills = set(extract_skills(resume_text))
    job_skills = set(extract_skills(job_description))
    matched = sorted(resume_skills & job_skills)
    missing = sorted(job_skills - resume_skills)

    skill_score = (len(matched) / len(job_skills) * 100) if job_skills else 0.0
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([resume_text, job_description])
    similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100
    overall = round((skill_score * 0.7) + (similarity * 0.3), 2)

    return {
        "overall_match_score": overall,
        "skill_match_score": round(skill_score, 2),
        "text_similarity_score": round(similarity, 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "resume_skills_detected": sorted(resume_skills),
        "job_skills_detected": sorted(job_skills),
        "retrieved_resume_evidence": retrieve_relevant_resume_sentences(resume_text, job_description),
    }
