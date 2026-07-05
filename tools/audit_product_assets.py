"""Audit mobile product artwork consistency and size.

The script is intentionally heuristic: it does not decide which image is
"bad", but it creates a repeatable shortlist for visual review.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "assets" / "images"
DOCS_DIR = ROOT / "docs"
CSV_PATH = DOCS_DIR / "product_asset_audit_2026-07-05.csv"
REPORT_PATH = DOCS_DIR / "PRODUCT_ASSET_AUDIT_2026-07-05.md"

LARGE_IMAGE_LIMIT = 120 * 1024
VERY_LARGE_IMAGE_LIMIT = 140 * 1024
CARD_BOTTOM_WHITE_LIMIT = 0.30
CARD_TOP_WHITE_LIMIT = 0.22
LOW_EDGE_SCORE_LIMIT = 12.0


@dataclass(frozen=True)
class AssetFinding:
    path: Path
    width: int
    height: int
    bytes_size: int
    bottom_white_ratio: float
    top_white_ratio: float
    edge_score: float
    style_guess: str
    priority: str
    reasons: tuple[str, ...]

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def kib(self) -> float:
        return self.bytes_size / 1024


def _white_ratio(image: Image.Image) -> float:
    sample = image.convert("RGB").resize((64, 64))
    data = sample.tobytes()
    white = sum(
        1
        for index in range(0, len(data), 3)
        if data[index] >= 232 and data[index + 1] >= 232 and data[index + 2] >= 220
    )
    return white / (64 * 64)


def _edge_score(image: Image.Image) -> float:
    gray = image.convert("L").resize((128, 128))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(edges).mean[0])


def _analyze_image(path: Path) -> AssetFinding:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        bottom = image.crop((0, int(height * 0.74), width, height))
        top_left = image.crop((0, 0, int(width * 0.45), int(height * 0.18)))
        bottom_white = _white_ratio(bottom)
        top_white = _white_ratio(top_left)
        edge = _edge_score(image)

    reasons: list[str] = []
    style_guess = "full-pop-art"
    if bottom_white >= CARD_BOTTOM_WHITE_LIMIT or top_white >= CARD_TOP_WHITE_LIMIT:
        style_guess = "card-template"
        reasons.append("widoczny szablon karty lub biala etykieta")
    if path.stat().st_size >= VERY_LARGE_IMAGE_LIMIT:
        reasons.append("bardzo duzy plik")
    elif path.stat().st_size >= LARGE_IMAGE_LIMIT:
        reasons.append("duzy plik")
    if edge <= LOW_EDGE_SCORE_LIMIT:
        reasons.append("niski poziom detalu wedlug heurystyki")

    if style_guess == "card-template":
        priority = "high"
    elif path.stat().st_size >= VERY_LARGE_IMAGE_LIMIT:
        priority = "medium"
    elif reasons:
        priority = "low"
    else:
        priority = "ok"

    return AssetFinding(
        path=path,
        width=width,
        height=height,
        bytes_size=path.stat().st_size,
        bottom_white_ratio=bottom_white,
        top_white_ratio=top_white,
        edge_score=edge,
        style_guess=style_guess,
        priority=priority,
        reasons=tuple(reasons),
    )


def _priority_key(finding: AssetFinding) -> tuple[int, int, str]:
    order = {"high": 0, "medium": 1, "low": 2, "ok": 3}
    return (order[finding.priority], -finding.bytes_size, finding.name.casefold())


def _write_csv(findings: list[AssetFinding]) -> None:
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "name",
                "file",
                "priority",
                "style_guess",
                "size_kib",
                "width",
                "height",
                "bottom_white_ratio",
                "top_white_ratio",
                "edge_score",
                "reasons",
            ]
        )
        for finding in sorted(findings, key=_priority_key):
            writer.writerow(
                [
                    finding.name,
                    finding.path.name,
                    finding.priority,
                    finding.style_guess,
                    f"{finding.kib:.1f}",
                    finding.width,
                    finding.height,
                    f"{finding.bottom_white_ratio:.3f}",
                    f"{finding.top_white_ratio:.3f}",
                    f"{finding.edge_score:.2f}",
                    "; ".join(finding.reasons),
                ]
            )


def _write_report(findings: list[AssetFinding]) -> None:
    total_size = sum(item.bytes_size for item in findings)
    by_priority = {
        priority: [item for item in findings if item.priority == priority]
        for priority in ("high", "medium", "low", "ok")
    }
    card_template = [item for item in findings if item.style_guess == "card-template"]
    biggest = sorted(findings, key=lambda item: item.bytes_size, reverse=True)[:15]
    review = sorted(
        [item for item in findings if item.priority in {"high", "medium"}],
        key=_priority_key,
    )[:60]

    lines = [
        "# Product Asset Audit - 2026-07-05",
        "",
        "Cel: przygotowac bezpieczna liste grafik produktow do podmiany bez mieszania tego z duzym refaktorem UI.",
        "",
        "## Podsumowanie",
        "",
        f"- Pliki WebP: {len(findings)}",
        f"- Laczy rozmiar katalogu `assets/images`: {total_size / 1024 / 1024:.2f} MiB",
        f"- Kandydaci high priority: {len(by_priority['high'])}",
        f"- Kandydaci medium priority: {len(by_priority['medium'])}",
        f"- Kandydaci low priority: {len(by_priority['low'])}",
        f"- Obrazy wygladajace jak szablon/karta: {len(card_template)}",
        "",
        "## Rekomendacja",
        "",
        "1. Najpierw podmieniac obrazy `high`: to glownie grafiki z widoczna ramka/etykieta karty, ktore odcinaja sie od finalnego stylu.",
        "2. Nowe grafiki trzymac jako WebP 512x512, cel 70-110 KiB, twardy limit 120 KiB na plik.",
        "3. Nie podmieniac automatycznie wszystkich obrazow naraz. Robic batchami po 20-40 sztuk i sprawdzac UI na telefonie.",
        "4. Zachowac nazwy plikow, zeby nie ruszac mapowania produktow ani logiki aplikacji.",
        "",
        "## Pierwsza kolejka do recznej wymiany",
        "",
        "| Priorytet | Plik | Rozmiar | Heurystyka | Powody |",
        "|---|---:|---:|---|---|",
    ]
    for item in review:
        reasons = "; ".join(item.reasons) or "-"
        lines.append(
            f"| {item.priority} | `{item.path.name}` | {item.kib:.1f} KiB | "
            f"{item.style_guess} | {reasons} |"
        )

    lines.extend(
        [
            "",
            "## Najwieksze pliki",
            "",
            "| Plik | Rozmiar | Priorytet |",
            "|---|---:|---|",
        ]
    )
    for item in biggest:
        lines.append(f"| `{item.path.name}` | {item.kib:.1f} KiB | {item.priority} |")

    lines.extend(
        [
            "",
            "## Dane szczegolowe",
            "",
            f"Pelna tabela CSV: `{CSV_PATH.relative_to(ROOT).as_posix()}`",
            "",
            "Uwaga: klasyfikacja jest heurystyczna. Ostateczna decyzja zostaje wizualna, szczegolnie przy produktach dodanych poza ksiazka.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    paths = sorted(IMAGES_DIR.glob("*.webp"), key=lambda path: path.name.casefold())
    findings = [_analyze_image(path) for path in paths]
    DOCS_DIR.mkdir(exist_ok=True)
    _write_csv(findings)
    _write_report(findings)
    print(f"Analysed {len(findings)} product assets")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(f"Wrote {CSV_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
