from pathlib import Path

from tools.verify_android_legal_bundle import CONTACT_EMAIL

ROOT = Path(__file__).resolve().parents[1]
OUTDATED_EMAIL = "milczarek.sebastian@gmail.com"


def test_legal_and_privacy_documents_use_current_contact():
    paths = (
        ROOT / "LICENSE",
        ROOT / "EULA",
        ROOT / "AI_USAGE_POLICY",
        ROOT / "THIRD_PARTY_NOTICES",
        ROOT / "REUSE.toml",
        ROOT / "LICENSES" / "LicenseRef-RefrigerationCalc-Proprietary-1.0.txt",
        ROOT / "docs" / "privacy.html",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert CONTACT_EMAIL in text, path
        assert OUTDATED_EMAIL not in text, path


def test_privacy_policy_discloses_nbp_and_optional_firebase():
    text = (ROOT / "docs" / "privacy.html").read_text(encoding="utf-8")

    assert "Kursy walut (API NBP)" in text
    assert "Exchange rates (NBP API)" in text
    assert "Firebase Crashlytics" in text
    assert "Firebase Remote Config" in text
    assert "Ostatnia aktualizacja: 21 lipca 2026 r." in text
    assert "Last updated: 21 July 2026." in text
