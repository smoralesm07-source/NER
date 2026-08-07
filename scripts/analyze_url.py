from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ner_prensa.pipeline import analyze_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output", default="docs/data/latest.json")
    args = parser.parse_args()

    result = analyze_url(args.url)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    llm_error = str(result.engine.get("llm_error", ""))
    if llm_error:
        print(f"AVISO LLM: {llm_error}", file=sys.stderr)
    print(
        f"OK: {len(result.entities)} entidades -> {out} "
        f"| GLiNER={'sí' if result.engine.get('gliner') else 'no'} "
        f"| LLM={'sí' if result.engine.get('llm') else 'no'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
