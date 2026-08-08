from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dependency_review_is_pinned_read_only_and_blocking():
    workflow = (ROOT / ".github/workflows/dependency-review.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "branches: [main, master]" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "pull-requests: write" not in workflow
    assert "actions/dependency-review-action@v" not in workflow
    assert (
        "actions/dependency-review-action@"
        "a1d282b36b6f3519aa1f3fc636f609c47dddb294 # v5.0.0"
    ) in workflow
    assert "fail-on-severity: moderate" in workflow


def test_dependabot_keeps_security_updates_separate_from_version_groups():
    config = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")

    assert "package-ecosystem: pip" in config
    assert "package-ecosystem: github-actions" in config
    assert config.count("applies-to: version-updates") == 2
    assert "applies-to: security-updates" not in config
    assert "open-pull-requests-limit: 5" in config


def test_codeql_scans_python_and_java_with_pinned_actions():
    workflow = (ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")

    assert "security-events: write" in workflow
    assert "contents: read" in workflow
    assert "pull-requests: write" not in workflow
    assert "language: python" in workflow
    assert "language: java-kotlin" in workflow
    assert workflow.count("build-mode: none") == 2
    assert "queries: security-extended" in workflow
    assert "github/codeql-action/init@v" not in workflow
    assert "github/codeql-action/analyze@v" not in workflow
    assert workflow.count(
        "github/codeql-action/"
        "init@5595ccaf912efad79be6eef63a5619ff05969be3 # v4.37.6"
    ) == 1
    assert workflow.count(
        "github/codeql-action/"
        "analyze@5595ccaf912efad79be6eef63a5619ff05969be3 # v4.37.6"
    ) == 1


def test_codeql_java_no_build_mode_cannot_silently_skip_kotlin():
    assert list((ROOT / "android").rglob("*.java"))
    assert not list((ROOT / "android").rglob("*.kt")), (
        "Kotlin requires changing the CodeQL java-kotlin job from no-build "
        "to autobuild or a manual Android build"
    )
