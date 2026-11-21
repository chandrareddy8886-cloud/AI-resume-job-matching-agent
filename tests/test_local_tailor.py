from app.services.local_tailor import build_local_tailored_resume


def test_local_fallback_uses_only_resume_evidence():
    resume = (
        "Candidate Name\n"
        "Python FastAPI PostgreSQL\n"
        "Built REST API endpoints using FastAPI and PostgreSQL.\n"
        "B.Tech Computer Science\n"
    )
    job = "Python FastAPI Docker cloud platforms"
    result = build_local_tailored_resume(resume, job)
    assert "ROLE-TARGETED RESUME DRAFT" in result
    assert "fastapi" in result.lower()
    assert "Built REST API endpoints using FastAPI and PostgreSQL." in result
    assert resume in result
    assert "AWS" not in result


def test_local_fallback_handles_no_skill_overlap():
    resume = "Candidate Name\nWorked on a student management project.\n"
    result = build_local_tailored_resume(resume, "Kubernetes and AWS administration")
    assert "the technical skills listed in the resume" in result
    assert resume in result
