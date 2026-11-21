from app.services.local_tailor import build_local_tailored_resume


def test_local_fallback_prioritizes_only_resume_evidence():
    resume = (
        "Candidate Name\n"
        "TECHNICAL SKILLS\nPython FastAPI PostgreSQL\n"
        "PROJECTS\nBuilt REST API endpoints using FastAPI and PostgreSQL.\n"
        "EDUCATION\nB.Tech Computer Science\n"
    )
    result = build_local_tailored_resume(resume, "Python FastAPI Docker backend development")
    assert "PROFESSIONAL SUMMARY" in result
    assert "FastAPI" in result
    assert "Built REST API endpoints using FastAPI and PostgreSQL." in result
    assert "B.Tech Computer Science" in result
    assert "AWS" not in result
    assert "Docker" not in result
    assert "RESUME DETAILS" not in result


def test_local_fallback_handles_no_skill_overlap_without_inventing_skills():
    resume = "Candidate Name\nWorked on a student management project.\n"
    result = build_local_tailored_resume(resume, "Kubernetes and AWS administration")
    assert "PROFILE" in result or "PROFESSIONAL SUMMARY" in result
    assert "student management project" in result.lower()
    assert "Kubernetes" not in result
    assert "AWS" not in result


def test_fallback_removes_duplicate_source_blocks_and_stale_objective():
    resume = (
        "K. Candidate\nHyderabad | candidate@example.com\n"
        "EDUCATION\nB.Tech Computer Science 2026\n"
        "TECHNICAL SKILLS\nPython | SQL (MySQL) | Git\n"
        "PROFESSIONAL SUMMARY\nSeeking a Python Developer Intern role.\n"
        "RELEVANT SKILLS\nPython\nSQL\n"
        "RESUME DETAILS\nK. Candidate\nOBJECTIVE\nSeeking a Python Developer Intern role.\n"
        "PROJECTS\nBuilt a Python expense tracker with file handling.\n"
        "CERTIFICATIONS AND SELF-STUDY\nPython Essentials 1 - Cisco\n"
    )
    jd = "Job Title: SQL and Python Production Support Engineer\nLocation: Bangalore\nSQL Python"
    result = build_local_tailored_resume(resume, jd)
    assert result.count("K. Candidate") == 1
    assert result.count("B.Tech Computer Science 2026") == 1
    assert "RESUME DETAILS" not in result
    assert "Python Developer Intern" not in result
    assert "Production Support Engineer" in result
    assert "Python expense tracker" in result


def test_summary_does_not_claim_missing_cloud_or_incident_experience():
    resume = "Candidate Name\nTECHNICAL SKILLS\nPython | SQL\nPROJECTS\nBuilt a Python data tool.\n"
    jd = "Job Title: SQL Python Cloud Production Support Engineer\nAWS incident management"
    result = build_local_tailored_resume(resume, jd)
    assert "AWS" not in result
    assert "incident management" not in result.lower()
