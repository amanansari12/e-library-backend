import json
import sys
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BOOKS_DIR = DATA_DIR / "books"

def calculate_sha256(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    print("Validating E-Library Catalog Data...")
    
    try:
        with open(DATA_DIR / "authors.json", "r", encoding="utf-8") as f:
            authors = json.load(f)
        with open(DATA_DIR / "categories.json", "r", encoding="utf-8") as f:
            categories = json.load(f)
        with open(DATA_DIR / "book_catalog.json", "r", encoding="utf-8") as f:
            books = json.load(f)
        with open(DATA_DIR / "sources.json", "r", encoding="utf-8") as f:
            sources = json.load(f)
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        sys.exit(1)
        
    author_names = {a["name"] for a in authors}
    category_names = {c["name"] for c in categories}
    
    if len(books) != 20:
        print(f"Error: Expected 20 books, found {len(books)}")
        sys.exit(1)
        
    demo_count = sum(1 for b in books if b.get("seed_demo"))
    if demo_count != 8:
        print(f"Error: Expected exactly 8 demo books, found {demo_count}")
        sys.exit(1)
        
    print(f"OK: Found {len(books)} books (8 demo, 12 developer assets).")
    
    filenames = set()
    for book in books:
        if book["author"] not in author_names:
            print(f"Error: Book '{book['title']}' references unknown author '{book['author']}'")
            sys.exit(1)
            
        for cat in book["categories"]:
            if cat not in category_names:
                print(f"Error: Book '{book['title']}' references unknown category '{cat}'")
                sys.exit(1)
                
        if book["filename"] in filenames:
            print(f"Error: Duplicate filename '{book['filename']}'")
            sys.exit(1)
        filenames.add(book["filename"])
        
        pdf_path = BOOKS_DIR / book["filename"]
        if not pdf_path.exists():
            print(f"Error: Missing PDF file '{pdf_path}'")
            sys.exit(1)
            
        if pdf_path.stat().st_size == 0:
            print(f"Error: PDF file '{pdf_path}' is empty")
            sys.exit(1)
            
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                print(f"Error: File '{pdf_path}' does not have a valid PDF header")
                sys.exit(1)
                
        calculated_sha = calculate_sha256(pdf_path)
        if book["sha256"] != calculated_sha:
            print(f"Error: SHA-256 mismatch for '{book['filename']}'")
            sys.exit(1)
            
    print("OK: All 20 books have valid authors, categories, and matching local PDFs.")
    
    if len(sources) != 20:
        print(f"Error: Expected 20 sources, found {len(sources)}")
        sys.exit(1)
        
    for source in sources:
        if "gutenberg_id" not in source or not source["source_url"]:
            print(f"Error: Source metadata missing for '{source['title']}'")
            sys.exit(1)
            
    print("OK: Source and provenance metadata validated.")
    print("Catalog validation SUCCESSFUL.")

if __name__ == "__main__":
    main()
