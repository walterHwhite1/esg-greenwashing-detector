from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CLIMATE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "climate": (
        "climate change",
        "climate risk",
        "global warming",
        "climate action",
    ),
    "emissions": (
        "greenhouse gas",
        "ghg emissions",
        "carbon emissions",
        "scope 1",
        "scope 2",
        "scope 3",
        "net zero",
        "decarbonization",
        "decarbonisation",
    ),
    "energy": (
        "renewable energy",
        "clean energy",
        "energy efficiency",
        "solar energy",
        "wind energy",
    ),
    "nature": (
        "biodiversity",
        "deforestation",
        "water stewardship",
        "waste reduction",
        "recycling",
        "circular economy",
    ),
    "targets": (
        "science-based target",
        "science based target",
        "carbon neutral",
        "emissions target",
        "reduction target",
    ),
}
def clean_text(text: str) -> str:
    """Clean text extracted from a PDF page."""

    # Join words that were split across lines, such as "renew-\nable".
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)

    # Replace repeated spaces, tabs, and line breaks with one space.
    text = re.sub(r"\s+", " ", text)

    return text.strip()

def find_keyword_matches(text: str) -> dict[str, list[str] | int]:
    """Find climate-related keywords and categories in text."""

    normalized_text = text.casefold()
    matched_keywords: list[str] = []
    matched_categories: list[str] = []

    for category, keywords in CLIMATE_KEYWORDS.items():
        category_found = False

        for keyword in keywords:
            pattern = rf"\b{re.escape(keyword)}\b"

            if re.search(pattern, normalized_text):
                matched_keywords.append(keyword)
                category_found = True

        if category_found:
            matched_categories.append(category)

    return {
        "matched_keywords": matched_keywords,
        "matched_categories": matched_categories,
        "keyword_count": len(matched_keywords),
    }
def filter_climate_pages(
    input_path: Path,
    output_directory: Path,
) -> Path:
    """Keep only pages containing climate-related keywords."""

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix.lower() != ".jsonl":
        raise ValueError("Input file must be a JSONL file.")

    output_directory.mkdir(parents=True, exist_ok=True)

    output_path = output_directory / (
        f"{input_path.stem}_climate.jsonl"
    )

    total_pages = 0
    climate_pages = 0

    with (
        input_path.open("r", encoding="utf-8") as input_file,
        output_path.open("w", encoding="utf-8") as output_file,
    ):
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue

            try:
                page_record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error}"
                ) from error

            total_pages += 1

            cleaned_text = clean_text(
                str(page_record.get("text", ""))
            )
            matches = find_keyword_matches(cleaned_text)

            if matches["keyword_count"] == 0:
                continue

            filtered_record = {
                **page_record,
                "text": cleaned_text,
                "character_count": len(cleaned_text),
                "has_text": bool(cleaned_text),
                **matches,
            }

            output_file.write(
                json.dumps(filtered_record, ensure_ascii=False)
                + "\n"
            )

            climate_pages += 1

    print(f"Input pages: {total_pages}")
    print(f"Climate-related pages: {climate_pages}")
    print(f"Filtered output saved to: {output_path}")

    return output_path
def parse_arguments() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Filter climate-related pages from an extracted "
            "PDF JSONL file."
        )
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the extracted page-level JSONL file.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/filtered"),
        help="Directory where the filtered JSONL file will be saved.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the climate filtering process."""

    arguments = parse_arguments()

    filter_climate_pages(
        input_path=arguments.input_path,
        output_directory=arguments.output_dir,
    )


if __name__ == "__main__":
    main()