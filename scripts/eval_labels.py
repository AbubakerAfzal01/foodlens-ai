"""Run label photos through the real pipeline and write a markdown test table.

Usage (from the project folder, with your .env set up):
    python scripts/eval_labels.py tests/labels --diet halal --allergies milk,peanuts
Put 8-10 label photos (jpg/png/webp) in tests/labels first. The table is saved to
docs/TEST_TABLE.md. Fill the last column by comparing each row with the real label.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import Config  # noqa: E402
from backend.routes import _sniff  # noqa: E402
from backend.services import engine, vision  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--diet", default="halal", choices=engine.DIETS)
    ap.add_argument("--allergies", default="")
    ap.add_argument("--out", default="docs/TEST_TABLE.md")
    args = ap.parse_args()
    allergies = [a.strip().lower() for a in args.allergies.split(",") if a.strip()]
    cfg = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
    provider = vision.get_provider(cfg)

    rows = ["| # | Photo | Ingredients read | Verdict | Allergy alerts | May-contain | Time | Correct? (you fill) |",
            "|---|---|---|---|---|---|---|---|"]
    files = sorted(p for p in Path(args.folder).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    for i, path in enumerate(files, 1):
        blob = path.read_bytes()
        mime = _sniff(blob)
        t0 = time.monotonic()
        try:
            if not mime:
                raise vision.VisionError("not a JPG/PNG/WebP file", 415, "UNSUPPORTED_MEDIA_TYPE")
            got = provider.extract(blob, mime)
            res = engine.analyze(got["ingredients"], args.diet, allergies, got["precautionary"])
            shown = ", ".join(got["ingredients"][:8]) + (" …" if len(got["ingredients"]) > 8 else "")
            row = [str(i), path.name, f"{len(got['ingredients'])}: {shown}" if got["ingredients"] else "none read",
                   res["verdict"], ", ".join(res["allergy_alerts"]) or "-",
                   "; ".join(p["text"] for p in res["precautionary"]) or "-"]
        except vision.VisionError as exc:
            row = [str(i), path.name, f"ERROR {exc.code}", "-", "-", "-"]
        row.append(f"{time.monotonic() - t0:.1f}s")
        row.append("")
        rows.append("| " + " | ".join(c.replace("|", "/") for c in row) + " |")
        print(rows[-1])

    header = f"Diet: {args.diet}. Selected allergies: {', '.join(allergies) or 'none'}. Provider: {cfg['VISION_PROVIDER']}"
    if cfg["VISION_PROVIDER"] == "gemini":
        header += f" ({cfg['GEMINI_MODEL']})"
    Path(args.out).write_text(f"# Test table\n\n{header}\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
