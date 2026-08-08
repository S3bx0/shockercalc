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
