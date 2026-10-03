import argparse
import hashlib
import json
from pathlib import Path

import pymupdf


def calculate_file_hash(file_path: Path) -> str:
    """Create a unique SHA-256 fingerprint for the PDF."""
    sha256 = hashlib.sha256()

    with file_path.open("rb") as pdf_file:
        for chunk in iter(lambda: pdf_file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def extract_pdf_pages(pdf_path: Path, output_directory: Path) -> Path:
    """Extract every PDF page and save it as a JSONL record."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("The input file must be a PDF.")

    output_directory.mkdir(parents=True, exist_ok=True)

    document_id = calculate_file_hash(pdf_path)
    output_path = output_directory / f"{pdf_path.stem}.jsonl"

    extracted_pages = []

    with pymupdf.open(pdf_path) as document:
        total_pages = len(document)

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text", sort=True).strip()

            page_record = {
                "document_id": document_id,
                "source_file": pdf_path.name,
                "page_number": page_number,
                "total_pages": total_pages,
                "text": text,
                "character_count": len(text),
                "has_text": bool(text),
            }

            extracted_pages.append(page_record)

    with output_path.open("w", encoding="utf-8") as output_file:
        for page_record in extracted_pages:
            output_file.write(
                json.dumps(page_record, ensure_ascii=False) + "\n"
            )

    pages_with_text = sum(page["has_text"] for page in extracted_pages)

    print(f"PDF: {pdf_path.name}")
    print(f"Total pages: {len(extracted_pages)}")
    print(f"Pages containing text: {pages_with_text}")
    print(f"Output saved to: {output_path}")

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF into page-level JSONL records."
    )

    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the PDF sustainability report.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/extracted"),
        help="Directory where the JSONL output will be saved.",
    )

    arguments = parser.parse_args()

    extract_pdf_pages(
        pdf_path=arguments.pdf_path,
        output_directory=arguments.output_dir,
    )


if __name__ == "__main__":
    main()