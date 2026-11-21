from app.services.resume_quality import validate_tailored_resume


def test_quality_gate_accepts_resume_that_preserves_source_facts():
    source = (
        "Candidate Name\nEmail: person@example.com\n"
        "PROJECTS\nBuilt a Python API in 2025 processing 120 records.\n"
        "GitHub: https://github.com/person/project\n"
        "EDUCATION\nBachelor of Technology in Computer Science, completed in 2025.\n"
        "TECHNICAL SKILLS\nPython, REST API development, SQL, Git and software testing."
    )
    draft = (
        "Candidate Name\nEmail: person@example.com\n"
        "PROFESSIONAL SUMMARY\n"
        "Computer Science graduate with project experience building a Python API.\n"
        "PROJECTS\nBuilt a Python API in 2025 processing 120 records.\n"
        "GitHub: https://github.com/person/project\n"
        "EDUCATION\nBachelor of Technology in Computer Science, completed in 2025.\n"
        "TECHNICAL SKILLS\nPython, REST API development, SQL, Git and software testing."
    )
    result = validate_tailored_resume(source, draft)
    assert result.passed
    assert result.issues == ()


def test_quality_gate_rejects_unsupported_skills():
    source = "Python developer with project experience building APIs."
    draft = (
        "Candidate Name\nPROFESSIONAL SUMMARY\n"
        "Python and Docker developer with hands-on Kubernetes experience.\n"
        "PROJECTS\nBuilt a Python API for a project."
    )
    result = validate_tailored_resume(source, draft)
    assert not result.passed
    assert any("skills not evidenced" in issue for issue in result.issues)


def test_quality_gate_rejects_dropped_dates_metrics_and_contact_links():
    source = (
        "Candidate Name\nEmail: person@example.com\n"
        "PROJECTS\nBuilt a Python API in 2024 processing 120 records.\n"
        "GitHub: https://github.com/person/project"
    )
    draft = (
        "Candidate Name\nPROFESSIONAL SUMMARY\n"
        "Computer Science graduate with software project experience.\n"
        "PROJECTS\nBuilt a Python API."
    )
    result = validate_tailored_resume(source, draft)
    assert not result.passed
    assert any("dates" in issue for issue in result.issues)
    assert any("numeric facts" in issue for issue in result.issues)
    assert any("email addresses" in issue for issue in result.issues)
    assert any("URLs" in issue for issue in result.issues)
