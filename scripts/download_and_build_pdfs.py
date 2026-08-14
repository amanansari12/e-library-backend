import json
import logging
import re
import sys
import urllib.request
import hashlib
from pathlib import Path
from fpdf import FPDF
from datetime import datetime, UTC

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Ensure required directories exist
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BOOKS_DIR = ROOT / "data" / "books"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

# Dataset definition
BOOKS_DEF = [
    {"title": "Pride and Prejudice", "author": "Jane Austen", "year": 1813, "categories": ["Classic Literature", "Romance"], "gutenberg_id": 1342, "filename": "pride-and-prejudice.pdf"},
    {"title": "Frankenstein; or, The Modern Prometheus", "author": "Mary Shelley", "year": 1818, "categories": ["Classic Literature", "Science Fiction", "Horror"], "gutenberg_id": 84, "filename": "frankenstein.pdf"},
    {"title": "The Time Machine", "author": "H. G. Wells", "year": 1895, "categories": ["Science Fiction", "Adventure"], "gutenberg_id": 35, "filename": "the-time-machine.pdf"},
    {"title": "The War of the Worlds", "author": "H. G. Wells", "year": 1898, "categories": ["Science Fiction", "Horror"], "gutenberg_id": 36, "filename": "the-war-of-the-worlds.pdf"},
    {"title": "The Adventures of Sherlock Holmes", "author": "Arthur Conan Doyle", "year": 1892, "categories": ["Mystery & Detective", "Classic Literature"], "gutenberg_id": 1661, "filename": "adventures-of-sherlock-holmes.pdf"},
    {"title": "Dracula", "author": "Bram Stoker", "year": 1897, "categories": ["Gothic Fiction", "Horror"], "gutenberg_id": 345, "filename": "dracula.pdf"},
    {"title": "The Picture of Dorian Gray", "author": "Oscar Wilde", "year": 1890, "categories": ["Gothic Fiction", "Drama"], "gutenberg_id": 174, "filename": "picture-of-dorian-gray.pdf"},
    {"title": "The Wonderful Wizard of Oz", "author": "L. Frank Baum", "year": 1900, "categories": ["Children's Literature", "Fantasy"], "gutenberg_id": 43936, "filename": "wonderful-wizard-of-oz.pdf"},
    {"title": "The Adventures of Tom Sawyer", "author": "Mark Twain", "year": 1876, "categories": ["Classic Literature", "Adventure", "Children's Literature"], "gutenberg_id": 74, "filename": "adventures-of-tom-sawyer.pdf"},
    {"title": "Adventures of Huckleberry Finn", "author": "Mark Twain", "year": 1884, "categories": ["Classic Literature", "Adventure"], "gutenberg_id": 76, "filename": "adventures-of-huckleberry-finn.pdf"},
    {"title": "Great Expectations", "author": "Charles Dickens", "year": 1861, "categories": ["Classic Literature", "Historical Fiction"], "gutenberg_id": 1400, "filename": "great-expectations.pdf"},
    {"title": "A Tale of Two Cities", "author": "Charles Dickens", "year": 1859, "categories": ["Classic Literature", "Historical Fiction"], "gutenberg_id": 98, "filename": "a-tale-of-two-cities.pdf"},
    {"title": "Oliver Twist", "author": "Charles Dickens", "year": 1838, "categories": ["Classic Literature", "Drama"], "gutenberg_id": 730, "filename": "oliver-twist.pdf"},
    {"title": "A Christmas Carol", "author": "Charles Dickens", "year": 1843, "categories": ["Classic Literature", "Fantasy"], "gutenberg_id": 46, "filename": "a-christmas-carol.pdf"},
    {"title": "The Secret Garden", "author": "Frances Hodgson Burnett", "year": 1911, "categories": ["Children's Literature", "Classic Literature"], "gutenberg_id": 113, "filename": "secret-garden.pdf"},
    {"title": "Little Women", "author": "Louisa May Alcott", "year": 1868, "categories": ["Classic Literature", "Drama"], "gutenberg_id": 514, "filename": "little-women.pdf"},
    {"title": "The Count of Monte Cristo", "author": "Alexandre Dumas", "year": 1844, "categories": ["Historical Fiction", "Adventure"], "gutenberg_id": 1184, "filename": "count-of-monte-cristo.pdf"},
    {"title": "Treasure Island", "author": "Robert Louis Stevenson", "year": 1883, "categories": ["Adventure", "Children's Literature"], "gutenberg_id": 120, "filename": "treasure-island.pdf"},
    {"title": "Jane Eyre", "author": "Charlotte Brontë", "year": 1847, "categories": ["Classic Literature", "Romance", "Gothic Fiction"], "gutenberg_id": 1260, "filename": "jane-eyre.pdf"},
    {"title": "Moby-Dick; or, The Whale", "author": "Herman Melville", "year": 1851, "categories": ["Classic Literature", "Adventure"], "gutenberg_id": 2701, "filename": "moby-dick.pdf"},
]

# Author Biographies
AUTHOR_METADATA = {
    "Jane Austen": {"biography": "English novelist known for her social commentary in novels including Pride and Prejudice.", "birth_year": 1775, "death_year": 1817},
    "Mary Shelley": {"biography": "English novelist who wrote the Gothic novel Frankenstein.", "birth_year": 1797, "death_year": 1851},
    "H. G. Wells": {"biography": "English writer. Prolific in many genres, he wrote dozens of novels, short stories, and works of social commentary.", "birth_year": 1866, "death_year": 1946},
    "Arthur Conan Doyle": {"biography": "British writer and physician, most noted for creating the fictional detective Sherlock Holmes.", "birth_year": 1859, "death_year": 1930},
    "Bram Stoker": {"biography": "Irish author, best known today for his 1897 Gothic horror novel Dracula.", "birth_year": 1847, "death_year": 1912},
    "Oscar Wilde": {"biography": "Irish poet and playwright. After writing in different forms throughout the 1880s, he became one of London's most popular playwrights in the early 1890s.", "birth_year": 1854, "death_year": 1900},
    "L. Frank Baum": {"biography": "American author chiefly known for his children's books, particularly The Wonderful Wizard of Oz.", "birth_year": 1856, "death_year": 1919},
    "Mark Twain": {"biography": "American writer, humorist, entrepreneur, publisher, and lecturer.", "birth_year": 1835, "death_year": 1910},
    "Charles Dickens": {"biography": "English writer and social critic. He created some of the world's best-known fictional characters.", "birth_year": 1812, "death_year": 1870},
    "Frances Hodgson Burnett": {"biography": "British-American novelist and playwright. She is best known for the three children's novels Little Lord Fauntleroy, A Little Princess, and The Secret Garden.", "birth_year": 1849, "death_year": 1924},
    "Louisa May Alcott": {"biography": "American novelist and poet best known as the author of the novel Little Women.", "birth_year": 1832, "death_year": 1888},
    "Alexandre Dumas": {"biography": "French writer. His works have been translated into many languages, and he is one of the most widely read French authors.", "birth_year": 1802, "death_year": 1870},
    "Robert Louis Stevenson": {"biography": "Scottish novelist and travel writer, most noted for Treasure Island, Kidnapped, and Strange Case of Dr Jekyll and Mr Hyde.", "birth_year": 1850, "death_year": 1894},
    "Charlotte Brontë": {"biography": "English novelist and poet, the eldest of the three Brontë sisters who survived into adulthood and whose novels became classics of English literature.", "birth_year": 1816, "death_year": 1855},
    "Herman Melville": {"biography": "American novelist, short story writer, and poet of the American Renaissance period.", "birth_year": 1819, "death_year": 1891},
}

CATEGORIES_METADATA = {
    "Classic Literature": "Enduring literary works of historical importance.",
    "Romance": "Narrative fiction focusing on romantic relationships.",
    "Science Fiction": "Imaginative fiction exploring future science and technology.",
    "Horror": "Fiction intended to frighten and unsettle.",
    "Mystery & Detective": "Fiction featuring the investigation of a crime or mystery.",
    "Gothic Fiction": "Dark fiction featuring mystery, horror, and the supernatural.",
    "Drama": "Plays and emotionally charged fiction.",
    "Children's Literature": "Literature written specifically for children.",
    "Fantasy": "Fiction featuring magical or supernatural elements.",
    "Adventure": "Stories of exciting journeys and action.",
    "Historical Fiction": "Stories set in the past that incorporate historical facts."
}


class PDF(FPDF):
    def header(self):
        # We only want a header on pages after the first page
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.cell(0, 10, self.title, align="C")
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def download_gutenberg_text(gutenberg_id: int) -> str:
    """Download plain text from Project Gutenberg."""
    # Common text URL patterns
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt",
    ]
    
    for url in urls:
        try:
            logging.info(f"Trying to download {url}")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8-sig', errors='replace')
                return content, url
        except Exception as e:
            logging.debug(f"Failed to download {url}: {e}")
            continue
    
    raise ValueError(f"Failed to download text for Gutenberg ID {gutenberg_id}")


def strip_gutenberg_headers(text: str) -> str:
    """Attempt to strip standard Gutenberg boilerplate."""
    # The header usually ends with something like "*** START OF THE PROJECT GUTENBERG EBOOK..."
    start_match = re.search(r"\*\*\*\s*START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.IGNORECASE)
    if start_match:
        text = text[start_match.end():]
        
    # The footer usually starts with "*** END OF THE PROJECT GUTENBERG EBOOK..."
    end_match = re.search(r"\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.IGNORECASE)
    if end_match:
        text = text[:end_match.start()]
        
    return text.strip()


def generate_pdf(title: str, author: str, content: str, output_path: Path):
    """Generate a readable PDF from plain text."""
    pdf = PDF()
    pdf.set_title(title)
    pdf.set_author(author)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title Page
    pdf.set_font("helvetica", "B", 24)
    pdf.cell(0, 60, "", ln=1)
    pdf.cell(0, 20, title.encode("latin-1", "replace").decode("latin-1"), align="C", ln=1)
    pdf.set_font("helvetica", "I", 16)
    pdf.cell(0, 15, f"By {author}".encode("latin-1", "replace").decode("latin-1"), align="C", ln=1)
    
    # Notice
    pdf.cell(0, 60, "", ln=1)
    pdf.set_font("helvetica", "", 10)
    notice = "Project Gutenberg edition; public-domain status indicated for the United States; verify local jurisdiction before redistribution."
    pdf.multi_cell(0, 5, notice, align="C")
    
    pdf.add_page()
    
    # Content
    pdf.set_font("helvetica", "", 11)
    
    # Process text in manageable chunks and replace characters that fpdf1 can't handle
    clean_text = content.replace('\r\n', '\n').replace('\r', '\n')
    # Convert some common unicode punctuation to ASCII equivalents for standard helvetica
    replacements = {
        '”': '"', '“': '"', '’': "'", '‘': "'", '—': '-', '…': '...',
        '–': '-', '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'"
    }
    for k, v in replacements.items():
        clean_text = clean_text.replace(k, v)
        
    # latin-1 encoding for standard PDF fonts
    encoded_text = clean_text.encode("latin-1", "replace").decode("latin-1")
    
    # Output text
    pdf.multi_cell(0, 6, encoded_text)
    
    pdf.output(str(output_path))


def calculate_sha256(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    books_data = []
    sources_data = []
    authors_data = [{"name": k, **v} for k, v in AUTHOR_METADATA.items()]
    categories_data = [{"name": k, "description": v} for k, v in CATEGORIES_METADATA.items()]
    
    success_count = 0
    
    for b in BOOKS_DEF:
        logging.info(f"Processing: {b['title']}")
        pdf_path = BOOKS_DIR / b['filename']
        
        try:
            if not pdf_path.exists():
                text_content, source_url = download_gutenberg_text(b['gutenberg_id'])
                clean_text = strip_gutenberg_headers(text_content)
                logging.info(f"Generating PDF for {b['title']}")
                generate_pdf(b['title'], b['author'], clean_text, pdf_path)
            else:
                logging.info(f"PDF already exists for {b['title']}, skipping generation.")
                source_url = f"https://www.gutenberg.org/ebooks/{b['gutenberg_id']}"
            
            sha256_hash = calculate_sha256(pdf_path)
            
            # Prepare book JSON
            books_data.append({
                "id": b["filename"].replace(".pdf", ""),
                "title": b["title"],
                "author": b["author"],
                "categories": b["categories"],
                "publication_year": b["year"],
                "file": f"books/{b['filename']}",
                "filename": b["filename"],
                "gutenberg_id": b["gutenberg_id"],
                "sha256": sha256_hash,
                "seed_demo": b["title"] in {
                    "Pride and Prejudice",
                    "Frankenstein; or, The Modern Prometheus",
                    "The Adventures of Sherlock Holmes",
                    "Dracula",
                    "The Wonderful Wizard of Oz",
                    "Treasure Island",
                    "A Tale of Two Cities",
                    "Moby-Dick; or, The Whale"
                }
            })
            
            # Prepare source JSON
            sources_data.append({
                "title": b["title"],
                "author": b["author"],
                "gutenberg_id": b["gutenberg_id"],
                "source_url": source_url,
                "format": "application/pdf (converted from Gutenberg plain text)",
                "license": "Project Gutenberg edition; public-domain status indicated for the United States; verify local jurisdiction before redistribution.",
                "verification_date": datetime.now(UTC).isoformat(),
                "filename": b["filename"],
                "sha256": sha256_hash,
                "notes": "PDF generated automatically from Gutenberg plain text."
            })
            
            success_count += 1
            
        except Exception as e:
            logging.error(f"Failed to process {b['title']}: {e}")
            sys.exit(1)
            
    # Write JSON metadata
    with open(DATA_DIR / "authors.json", "w", encoding="utf-8") as f:
        json.dump(authors_data, f, indent=2, ensure_ascii=False)
        
    with open(DATA_DIR / "categories.json", "w", encoding="utf-8") as f:
        json.dump(categories_data, f, indent=2, ensure_ascii=False)
        
    with open(DATA_DIR / "book_catalog.json", "w", encoding="utf-8") as f:
        json.dump(books_data, f, indent=2, ensure_ascii=False)
        
    with open(DATA_DIR / "sources.json", "w", encoding="utf-8") as f:
        json.dump(sources_data, f, indent=2, ensure_ascii=False)
        
    logging.info(f"Successfully processed {success_count} out of {len(BOOKS_DEF)} books.")

if __name__ == "__main__":
    main()
