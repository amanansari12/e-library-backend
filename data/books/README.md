# Book Catalog Assets

These PDFs are reusable local test/demo assets. They are tracked in Git as repository-owned catalog assets.

## Runtime vs. Catalog

* **Catalog Assets (data/books/)**: The 20 real PDFs available for developers to test with.
* **Runtime Storage (storage/books/)**: Application-managed runtime files. Not tracked by Git.

Only 8 of these 20 books are automatically inserted into the database via scripts/seed.py as a default demonstration dataset. The other 12 are developer assets.

## How to use a Developer Asset

To test the book creation/upload workflow manually:

1. Select a book from ../book_catalog.json or ../../docs/BOOK_CATALOG.md that is marked as a DEVELOPER ASSET.
2. Find its corresponding PDF in this folder.
3. Authenticate using the Admin user.
4. Use the POST /api/v1/books endpoint to create the book metadata.
5. Use the POST /api/v1/books/{id}/files endpoint to upload the selected PDF from this folder.
6. The application will process it and place the managed file under storage/books/{book_id}/<storage_key>/canonical.pdf.

**Example:**
I want to test "Jane Eyre".

* Author: Charlotte Brontë
* Categories: Classic Literature, Romance, Gothic Fiction
* PDF: data/books/jane-eyre.pdf

Create the book via the API, then upload jane-eyre.pdf as the digital file content.
