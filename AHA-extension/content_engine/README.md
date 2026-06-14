# AHA Content Engine

Package raw content files into a deployment-ready ZIP that slots directly into the AHA vault — no renaming, no reorganising.

---

## Requirements

- **Python 3.10 or later** — no external packages needed, stdlib only.
- The `aha/storage_vault.py` file must be present at `<project_root>/aha/storage_vault.py` (it is already there in this repo).

---

## Supported File Types

| Type  | Extensions                          | Vault output |
|-------|-------------------------------------|--------------|
| Text  | `.txt` `.md`                        | `{day}AI.txt` |
| Image | `.png` `.jpg` `.jpeg` `.webp` `.gif`| `{day}AI.png` |
| Video | `.mp4` `.mov` `.webm`               | `{day}AI.mp4` |

Any other extension is silently skipped and listed in the summary.

---

## Vault Naming Convention

The engine uses the `ai_pro` plan with suffix `AI`:

```
AI Pro/
  <Platform>/
    Texts/   → 1AI.txt,  2AI.txt,  … 30AI.txt
    Images/  → 1AI.png,  2AI.png,  … 30AI.png
    Videos/  → 1AI.mp4,  2AI.mp4,  … 30AI.mp4
```

Valid platforms: **LinkedIn**, **Instagram**, **Facebook**, **X**, **WhatsApp**

---

## Running the CLI

```bash
cd AHA-extension/content_engine

python engine.py \
  --input-dir ./raw_content \
  --platform LinkedIn \
  --month 7 \
  --year 2026 \
  --output ./output
```

### All flags

| Flag            | Required | Default    | Description                                                                     |
|-----------------|----------|------------|---------------------------------------------------------------------------------|
| `--input-dir`   | ✅        | —          | Directory containing your raw content files                                     |
| `--platform`    | ✅        | —          | One of: `LinkedIn`, `Instagram`, `Facebook`, `X`, `WhatsApp`                   |
| `--month`       | ✅        | —          | Month number 1–12                                                               |
| `--year`        | ✅        | —          | Four-digit year, e.g. `2026`                                                    |
| `--output`      | ❌        | `./output` | Directory where the ZIP is written (created automatically)                      |
| `--manifest`    | ❌        | auto-detect| Path to a `manifest.csv` for precise day assignment (see below)                 |

---

## Two Modes of Operation

### Mode 1 — Auto-scan (no manifest)

Drop your files into the input directory. The engine:

1. Groups files by type (text / image / video).
2. Sorts each group **alphabetically** by filename.
3. Assigns **day 1, 2, 3 …** sequentially within each group.

```
raw_content/
  a_intro.txt       → day 1 text  (1AI.txt)
  b_update.txt      → day 2 text  (2AI.txt)
  c_promo.txt       → day 3 text  (3AI.txt)
  banner1.png       → day 1 image (1AI.png)
  banner2.jpg       → day 2 image (2AI.png)
  reel.mp4          → day 1 video (1AI.mp4)
```

> Days with no content for a given type are simply skipped — no error.

### Mode 2 — Manifest CSV (precise control)

Create a `manifest.csv` in your input directory (or pass `--manifest path/to/file.csv`).

Copy and rename `manifest_template.csv` to get started:

```bash
cp manifest_template.csv raw_content/manifest.csv
```

**Format:**

```csv
filename,day,type
my_post_text.txt,1,text
my_image_day1.png,1,image
promo_video.mp4,3,video
caption_day2.txt,2,text
```

| Column     | Required | Values                              |
|------------|----------|-------------------------------------|
| `filename` | ✅        | Exact filename in `--input-dir`      |
| `day`      | ✅        | Integer 1–366                        |
| `type`     | ❌        | `text` / `image` / `video` (inferred from extension if omitted) |

**Rules:**
- Each `(day, type)` combination must be unique — duplicates raise an error.
- If a filename in the manifest is not found in `--input-dir`, the engine exits with a clear error.
- If `type` is omitted or blank, the type is inferred from the file extension.

If a `manifest.csv` is present in `--input-dir`, it is used automatically even without `--manifest`.

---

## Example Commands

```bash
# LinkedIn content, July 2026, auto-scan
python engine.py --input-dir ./july_linkedin --platform LinkedIn --month 7 --year 2026

# Instagram with manifest, custom output directory
python engine.py \
  --input-dir ./insta_july \
  --platform Instagram \
  --month 7 --year 2026 \
  --manifest ./insta_july/manifest.csv \
  --output ~/Desktop/packages

# WhatsApp content, accept platform key (lowercase) instead of display name
python engine.py --input-dir ./wa_content --platform whatsapp --month 8 --year 2026
```

---

## Output ZIP Structure

The ZIP is named `{Platform}_{MM}_{YYYY}.zip` and contains the exact vault tree:

```
LinkedIn_07_2026.zip
  AI Pro/
    LinkedIn/
      Texts/
        1AI.txt
        2AI.txt
        …
      Images/
        1AI.png
        …
      Videos/
        1AI.mp4
        …
```

---

## Importing the ZIP into the AHA Vault

Simply unzip into `~/Downloads/aha/`:

```bash
# macOS / Linux
unzip LinkedIn_07_2026.zip -d ~/Downloads/aha/

# Or double-click the ZIP in Finder, then drag the AI Pro/ folder into ~/Downloads/aha/
```

The files will land exactly where the vault expects them — no further steps needed.

---

## Sample Summary Output

```
========================================================
  AHA Content Engine — Packaging Summary
========================================================
  Platform : LinkedIn
  Period   : 07/2026
  Days     : 3  [1, 2, 3]
  Texts    : 3
  Images   : 2
  Videos   : 1
  Total    : 6 file(s) packaged

  Output   : /Users/you/output/LinkedIn_07_2026.zip
========================================================
```

---

## Error Messages

| Situation | Message |
|-----------|---------|
| Invalid platform name | `[engine] Invalid platform 'Snapchat'. Allowed values: Facebook, Instagram, LinkedIn, WhatsApp, X` |
| File listed in manifest not found | `[engine] manifest row 4: file not found in input directory: '...'` |
| Duplicate day-slot in manifest | `[engine] Duplicate assignment: day 2 / image is claimed by both ...` |
| Empty input directory | `[engine] No supported content files found. Nothing to package.` |
| storage_vault.py missing | `[engine] Cannot import storage_vault.py. Searched paths: [...]` |

---

## Project Layout

```
AHA-extension/
  content_engine/
    engine.py               ← main CLI script
    manifest_template.csv   ← copy + edit for manifest mode
    README.md               ← this file
```
