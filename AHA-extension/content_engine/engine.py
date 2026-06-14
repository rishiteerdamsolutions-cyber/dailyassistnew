#!/usr/bin/env python3
"""
AHA Content Engine — engine.py
===============================
Renames raw content files using the AHA vault naming convention and packages
them into a ZIP that mirrors the exact vault folder structure.

Usage
-----
    python engine.py --input-dir ./raw_content --platform LinkedIn \
                     --month 7 --year 2026 --output ./output

The output ZIP can be unzipped directly into ~/Downloads/aha/ to populate the
vault without any further renaming.

Requirements: Python 3.10+, stdlib only (no pip installs needed).
"""

from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Import constants from storage_vault.py (sibling project: aha/).
# We locate the vault module relative to this file's location so the engine
# works regardless of where Python is invoked from.
# ---------------------------------------------------------------------------

_VAULT_MODULE_SEARCH_PATHS: list[Path] = [
    # AHA-extension/content_engine/ -> up two levels -> project root -> aha/
    Path(__file__).resolve().parent.parent.parent / "aha",
    # Fallback: one level up from this file
    Path(__file__).resolve().parent.parent / "aha",
]

_vault_module_dir: Path | None = None
for _candidate in _VAULT_MODULE_SEARCH_PATHS:
    if (_candidate / "storage_vault.py").exists():
        _vault_module_dir = _candidate
        break

if _vault_module_dir is None:
    # Last-resort: walk up to find aha/storage_vault.py
    _here = Path(__file__).resolve()
    for _parent in _here.parents:
        if (_parent / "aha" / "storage_vault.py").exists():
            _vault_module_dir = _parent / "aha"
            break

if _vault_module_dir is not None and str(_vault_module_dir) not in sys.path:
    sys.path.insert(0, str(_vault_module_dir))

try:
    from storage_vault import (  # type: ignore[import]
        MEDIA_DIR,
        MEDIA_EXT,
        PLAN_DIR,
        PLAN_SUFFIX,
        PLATFORM_DIR,
    )
except ModuleNotFoundError as _exc:
    raise SystemExit(
        "[engine] Cannot import storage_vault.py.\n"
        f"Searched paths: {[str(p) for p in _VAULT_MODULE_SEARCH_PATHS]}\n"
        f"Original error: {_exc}\n\n"
        "Make sure storage_vault.py exists at  <project_root>/aha/storage_vault.py"
    ) from _exc

# ---------------------------------------------------------------------------
# Internal constants derived from vault definitions
# ---------------------------------------------------------------------------

_PLAN: Literal["ai_pro"] = "ai_pro"
_SUFFIX: str = PLAN_SUFFIX[_PLAN]     # "AI"
_PLAN_DIR: str = PLAN_DIR[_PLAN]      # "AI Pro"

# Map of lowercase extension -> MediaKey
_EXT_TO_MEDIA: dict[str, str] = {
    ".txt": "text",
    ".md": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
}

# Canonical output extensions from vault (text->.txt, image->.png, video->.mp4)
_VAULT_EXT: dict[str, str] = MEDIA_EXT

# Valid display names for platforms (from PLATFORM_DIR values)
_VALID_PLATFORM_DISPLAY: dict[str, str] = {
    v.lower(): v for v in PLATFORM_DIR.values()
}
# Map display name -> PlatformKey
_DISPLAY_TO_KEY: dict[str, str] = {
    v: k for k, v in PLATFORM_DIR.items()
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ContentFile:
    """A single raw input file resolved to a vault slot."""

    source_path: Path
    day: int
    media_key: str   # "text" | "image" | "video"

    @property
    def vault_stem(self) -> str:
        return f"{self.day}{_SUFFIX}"

    @property
    def vault_ext(self) -> str:
        return _VAULT_EXT[self.media_key]

    @property
    def vault_filename(self) -> str:
        return f"{self.vault_stem}{self.vault_ext}"


@dataclass
class PackageSummary:
    platform_display: str
    month: int
    year: int
    text_count: int = 0
    image_count: int = 0
    video_count: int = 0
    days: set[int] = field(default_factory=set)
    skipped_files: list[str] = field(default_factory=list)
    zip_path: Path | None = None

    def record(self, cf: ContentFile) -> None:
        self.days.add(cf.day)
        if cf.media_key == "text":
            self.text_count += 1
        elif cf.media_key == "image":
            self.image_count += 1
        elif cf.media_key == "video":
            self.video_count += 1

    def print(self) -> None:
        total = self.text_count + self.image_count + self.video_count
        print("\n" + "=" * 56)
        print("  AHA Content Engine — Packaging Summary")
        print("=" * 56)
        print(f"  Platform : {self.platform_display}")
        print(f"  Period   : {self.month:02d}/{self.year}")
        print(f"  Days     : {len(self.days)}  {sorted(self.days)}")
        print(f"  Texts    : {self.text_count}")
        print(f"  Images   : {self.image_count}")
        print(f"  Videos   : {self.video_count}")
        print(f"  Total    : {total} file(s) packaged")
        if self.skipped_files:
            print(f"\n  Skipped  : {len(self.skipped_files)} unsupported file(s)")
            for sf in self.skipped_files:
                print(f"    - {sf}")
        if self.zip_path:
            print(f"\n  Output   : {self.zip_path.resolve()}")
        print("=" * 56 + "\n")


# ---------------------------------------------------------------------------
# Manifest parsing
# ---------------------------------------------------------------------------

def _infer_media_key(filename: str) -> str | None:
    """Return MediaKey for a filename based on its extension, or None."""
    ext = Path(filename).suffix.lower()
    return _EXT_TO_MEDIA.get(ext)


def _parse_manifest(manifest_path: Path, input_dir: Path) -> list[ContentFile]:
    """
    Parse manifest.csv -> list[ContentFile].

    Expected columns: filename, day, type
    'type' is optional — inferred from extension when absent or empty.
    Duplicate (day, media_key) pairs are rejected with a clear error.
    """
    content_files: list[ContentFile] = []
    seen: dict[tuple[int, str], str] = {}   # (day, media_key) -> filename

    with manifest_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        required = {"filename", "day"}
        if reader.fieldnames is None:
            raise SystemExit("[engine] manifest.csv appears to be empty or has no header row.")

        header_lower = {f.strip().lower() for f in reader.fieldnames}
        missing = required - header_lower
        if missing:
            raise SystemExit(
                f"[engine] manifest.csv is missing required column(s): {missing}\n"
                "Expected header: filename,day,type"
            )

        for row_num, raw_row in enumerate(reader, start=2):
            # Normalise keys
            row = {k.strip().lower(): (v or "").strip() for k, v in raw_row.items()}

            filename = row.get("filename", "").strip()
            day_raw = row.get("day", "").strip()
            type_raw = row.get("type", "").strip().lower()

            if not filename:
                print(f"  [warn] manifest row {row_num}: empty filename — skipped.")
                continue

            # Resolve day
            try:
                day = int(day_raw)
            except ValueError:
                raise SystemExit(
                    f"[engine] manifest row {row_num}: invalid day value '{day_raw}' "
                    f"for file '{filename}'. Day must be an integer."
                )
            if day < 1 or day > 366:
                raise SystemExit(
                    f"[engine] manifest row {row_num}: day {day} out of range [1, 366] "
                    f"for file '{filename}'."
                )

            # Resolve media key
            if type_raw in ("text", "image", "video"):
                media_key = type_raw
            else:
                media_key = _infer_media_key(filename)
                if media_key is None:
                    print(
                        f"  [warn] manifest row {row_num}: cannot determine type for "
                        f"'{filename}' — skipped."
                    )
                    continue

            # Resolve source path
            source_path = input_dir / filename
            if not source_path.is_file():
                raise SystemExit(
                    f"[engine] manifest row {row_num}: file not found in input directory: "
                    f"'{source_path}'"
                )

            # Duplicate check
            slot_key = (day, media_key)
            if slot_key in seen:
                raise SystemExit(
                    f"[engine] Duplicate assignment: day {day} / {media_key} is claimed by both "
                    f"'{seen[slot_key]}' and '{filename}'. Each day-slot can only hold one file "
                    f"per media type."
                )
            seen[slot_key] = filename

            content_files.append(ContentFile(source_path=source_path, day=day, media_key=media_key))

    return content_files


# ---------------------------------------------------------------------------
# Auto-scan (no manifest)
# ---------------------------------------------------------------------------

def _scan_input_dir(input_dir: Path) -> tuple[list[ContentFile], list[str]]:
    """
    Scan input_dir for content files.

    Files are sorted alphabetically within each media type group, then
    assigned sequential day numbers starting at 1 per type.

    Returns (content_files, skipped_names).
    """
    by_type: dict[str, list[Path]] = {"text": [], "image": [], "video": []}
    skipped: list[str] = []

    for p in sorted(input_dir.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_file():
            continue
        # Skip manifest.csv itself
        if p.name.lower() == "manifest.csv":
            continue
        media_key = _infer_media_key(p.name)
        if media_key is None:
            skipped.append(p.name)
            continue
        by_type[media_key].append(p)

    content_files: list[ContentFile] = []
    for media_key, paths in by_type.items():
        for day_idx, path in enumerate(paths, start=1):
            content_files.append(ContentFile(source_path=path, day=day_idx, media_key=media_key))

    return content_files, skipped


# ---------------------------------------------------------------------------
# ZIP builder
# ---------------------------------------------------------------------------

def _vault_arc_path(content_file: ContentFile, platform_display: str) -> str:
    """
    Return the archive-internal path for a ContentFile.

    Structure:
        AI Pro/<Platform>/Texts|Images|Videos/{day}AI.ext
    """
    media_dir = MEDIA_DIR[content_file.media_key]   # "Texts" | "Images" | "Videos"
    return f"{_PLAN_DIR}/{platform_display}/{media_dir}/{content_file.vault_filename}"


def build_zip(
    content_files: list[ContentFile],
    platform_display: str,
    output_dir: Path,
    month: int,
    year: int,
) -> Path:
    """Create the ZIP archive and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"{platform_display}_{month:02d}_{year}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cf in content_files:
            arc_path = _vault_arc_path(cf, platform_display)
            zf.write(cf.source_path, arcname=arc_path)

    return zip_path


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _resolve_platform(raw: str) -> tuple[str, str]:
    """
    Validate the platform argument and return (display_name, platform_key).

    Accepts both display names (LinkedIn) and internal keys (linkedin).
    Raises SystemExit with a clear message on failure.
    """
    normalised = raw.strip().lower()

    # Try as platform key first
    if normalised in PLATFORM_DIR:
        key = normalised
        display = PLATFORM_DIR[key]
        return display, key

    # Try as display name (case-insensitive)
    display = _VALID_PLATFORM_DISPLAY.get(normalised)
    if display is not None:
        key = _DISPLAY_TO_KEY[display]
        return display, key

    valid = sorted(PLATFORM_DIR.values())
    raise SystemExit(
        f"[engine] Invalid platform '{raw}'.\n"
        f"Allowed values: {', '.join(valid)}"
    )


def _validate_month(value: str) -> int:
    try:
        m = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Month must be an integer, got '{value}'.")
    if not 1 <= m <= 12:
        raise argparse.ArgumentTypeError(f"Month must be between 1 and 12, got {m}.")
    return m


def _validate_year(value: str) -> int:
    try:
        y = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Year must be an integer, got '{value}'.")
    if not 2020 <= y <= 2100:
        raise argparse.ArgumentTypeError(f"Year must be between 2020 and 2100, got {y}.")
    return y


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="engine",
        description=(
            "AHA Content Engine — renames raw content files using the AHA vault "
            "naming convention and packages them into a deployment-ready ZIP."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Auto-scan (alphabetical order -> sequential days):
    python engine.py --input-dir ./raw_content --platform LinkedIn
                     --month 7 --year 2026 --output ./output

  Use manifest.csv for precise day assignment:
    python engine.py --input-dir ./raw_content --platform Instagram
                     --month 7 --year 2026 --manifest ./raw_content/manifest.csv
                     --output ./output

Unzip into vault:
  unzip LinkedIn_07_2026.zip -d ~/Downloads/aha/
        """,
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        metavar="DIR",
        help="Directory containing raw content files.",
    )
    parser.add_argument(
        "--platform",
        required=True,
        metavar="PLATFORM",
        help=(
            "Target social media platform. "
            "Allowed: LinkedIn, Instagram, Facebook, X, WhatsApp."
        ),
    )
    parser.add_argument(
        "--month",
        required=True,
        type=_validate_month,
        metavar="N",
        help="Content month (1-12).",
    )
    parser.add_argument(
        "--year",
        required=True,
        type=_validate_year,
        metavar="YYYY",
        help="Content year (e.g. 2026).",
    )
    parser.add_argument(
        "--output",
        default=Path("./output"),
        type=Path,
        metavar="DIR",
        help="Output directory for the ZIP file. Created if it does not exist. (default: ./output)",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        type=Path,
        metavar="CSV",
        help=(
            "Path to a manifest.csv with columns: filename, day, type. "
            "If omitted, the engine auto-scans --input-dir and assigns days alphabetically."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Validate inputs
    input_dir: Path = args.input_dir.resolve()
    if not input_dir.exists():
        raise SystemExit(f"[engine] --input-dir does not exist: '{input_dir}'")
    if not input_dir.is_dir():
        raise SystemExit(f"[engine] --input-dir is not a directory: '{input_dir}'")

    platform_display, _platform_key = _resolve_platform(args.platform)
    month: int = args.month
    year: int = args.year
    output_dir: Path = args.output.resolve()

    print("\n[engine] AHA Content Engine starting ...")
    print(f"  Input dir  : {input_dir}")
    print(f"  Platform   : {platform_display}")
    print(f"  Period     : {month:02d}/{year}")

    # Collect content files
    skipped: list[str] = []

    # Decide source: explicit manifest flag -> manifest.csv in input dir -> auto-scan
    manifest_path: Path | None = None
    if args.manifest is not None:
        manifest_path = args.manifest.resolve()
        if not manifest_path.is_file():
            raise SystemExit(f"[engine] Manifest file not found: '{manifest_path}'")
    elif (input_dir / "manifest.csv").is_file():
        manifest_path = input_dir / "manifest.csv"
        print(f"  Manifest   : {manifest_path} (auto-detected)")

    if manifest_path is not None:
        print(f"  Mode       : manifest  ({manifest_path.name})")
        content_files = _parse_manifest(manifest_path, input_dir)
    else:
        print("  Mode       : auto-scan (alphabetical)")
        content_files, skipped = _scan_input_dir(input_dir)

    if not content_files:
        raise SystemExit(
            "[engine] No supported content files found. Nothing to package.\n"
            "Supported extensions:\n"
            "  Text  : .txt .md\n"
            "  Image : .png .jpg .jpeg .webp .gif\n"
            "  Video : .mp4 .mov .webm"
        )

    # Duplicate-slot guard (belt-and-suspenders for manifest mode)
    seen_slots: dict[tuple[int, str], str] = {}
    for cf in content_files:
        key = (cf.day, cf.media_key)
        if key in seen_slots:
            raise SystemExit(
                f"[engine] Duplicate slot detected: day {cf.day} / {cf.media_key} "
                f"is assigned to both '{seen_slots[key]}' and '{cf.source_path.name}'."
            )
        seen_slots[key] = cf.source_path.name

    # Build summary
    summary = PackageSummary(
        platform_display=platform_display,
        month=month,
        year=year,
        skipped_files=skipped,
    )
    for cf in content_files:
        summary.record(cf)

    # Build ZIP
    print(f"\n[engine] Packaging {len(content_files)} file(s) into ZIP ...")
    zip_path = build_zip(content_files, platform_display, output_dir, month, year)
    summary.zip_path = zip_path

    # Print summary
    summary.print()


if __name__ == "__main__":
    main()
