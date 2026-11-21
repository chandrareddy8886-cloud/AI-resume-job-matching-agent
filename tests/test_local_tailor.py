from app.services.local_tailor import build_local_tailored_resume


def test_local_fallback_prioritizes_only_resume_evidence():
    resume = (
        "Candidate Name\n"
        "TECHNICAL SKILLS\nPython FastAPI PostgreSQL\n"
        "PROJECTS\nBuilt REST API endpoints using FastAPI and PostgreSQL.\n"
        "EDUCATION\nB.Tech Computer Science\n"
    )
    result = build_local_tailored_resume(resume, "Python FastAPI Docker cloud platforms")
    assert "PROFESSIONAL SUMMARY" in result
    assert "fastapi" in result.lower()
    assert "Built REST API endpoints using FastAPI and PostgreSQL." in result
    assert "B.Tech Computer Science" in result
    assert "AWS" not in result
    assert "Docker" not in result


def test_local_fallback_handles_no_skill_overlap_without_inventing_skills():
    resume = "Candidate Name\nWorked on a student management project.\n"
    result = build_local_tailored_resume(resume, "Kubernetes and AWS administration")
    assert "PROFESSIONAL SUMMARY" in result
    assert "student management project" in result
    assert "Kubernetes" not in result
    assert "AWS" not in result
