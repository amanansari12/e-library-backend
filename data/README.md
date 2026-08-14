# E-Library Catalog Data

This directory contains the canonical catalog data for the E-Library project, designed to provide a realistic, interviewer-ready demonstration environment with legitimate assets.

## Structure

* `books.json`: Core catalog defining 20 real public-domain works.
* `authors.json`: Validated metadata for the authors of the 20 works.
* `categories.json`: Realistic categories mapped to the books.
* `sources.json`: Legal/provenance metadata and SHA-256 checksums mapping the books to their origins (e.g. Project Gutenberg) and local digital assets.

## Adding a New Book

To add a new legitimate book to the catalog for local use:
1. Identify a public domain or open-license work.
2. Download the text and convert it to PDF (e.g., using `scripts/download_and_build_pdfs.py`).
3. Place the PDF in `storage/books/<filename>.pdf`.
4. Create an entry in `books.json` with the title, author, category, publication year, and SHA-256 checksum.
5. Create an entry in `sources.json` to record its legal status and source URL.
6. Ensure the author exists in `authors.json` and any assigned categories exist in `categories.json`.
7. Re-run `python scripts/seed.py` to sync the database.
