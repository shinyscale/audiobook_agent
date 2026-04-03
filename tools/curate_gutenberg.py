#!/usr/bin/env python3
"""
curate_gutenberg.py — Download and catalog Gutenberg texts for scalpel distillation.

Downloads 75-100 public domain novels via the Gutendex API, selected for:
- Genre diversity (detective, gothic, romance, adventure, literary, epistolary, sci-fi)
- POV diversity (first-person, third-person, omniscient, epistolary)
- Moral complexity (clear antagonists, morally ambiguous characters, victims)

Output:
  tools/gutenberg_corpus/*.txt          — raw text files
  tools/gutenberg_corpus/corpus_metadata.json  — metadata mapping
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CORPUS_DIR = Path(__file__).parent / "gutenberg_corpus"

# Curated book list: (gutenberg_id, title, author, expected_pov, genre)
# Expand beyond the plan's starter list to reach 75-100 books.
CURATED_BOOKS = [
    # First-person narration
    (1260, "Jane Eyre", "Charlotte Bronte", "first_person", "gothic_romance"),
    (1400, "Great Expectations", "Charles Dickens", "first_person", "literary"),
    (2701, "Moby Dick", "Herman Melville", "first_person", "adventure"),
    (1661, "The Adventures of Sherlock Holmes", "Arthur Conan Doyle", "first_person", "detective"),
    (2148, "The Tell-Tale Heart and Other Writings", "Edgar Allan Poe", "first_person", "gothic"),
    (521, "Robinson Crusoe", "Daniel Defoe", "first_person", "adventure"),
    (829, "Gulliver's Travels", "Jonathan Swift", "first_person", "satire"),
    (36, "The War of the Worlds", "H.G. Wells", "first_person", "sci-fi"),
    (5200, "Metamorphosis", "Franz Kafka", "third_person", "literary"),
    (11, "Alice's Adventures in Wonderland", "Lewis Carroll", "third_person", "fantasy"),
    (76, "Adventures of Huckleberry Finn", "Mark Twain", "first_person", "adventure"),
    (1952, "The Yellow Wallpaper", "Charlotte Perkins Gilman", "first_person", "gothic"),
    (209, "The Turn of the Screw", "Henry James", "first_person", "gothic"),
    (174, "The Picture of Dorian Gray", "Oscar Wilde", "third_person", "gothic"),
    (244, "A Study in Scarlet", "Arthur Conan Doyle", "first_person", "detective"),
    (2852, "The Hound of the Baskervilles", "Arthur Conan Doyle", "first_person", "detective"),
    (1342, "Pride and Prejudice", "Jane Austen", "third_person", "romance"),
    (2554, "Crime and Punishment", "Fyodor Dostoevsky", "third_person", "literary"),
    (1399, "Anna Karenina", "Leo Tolstoy", "third_person", "literary"),
    (730, "Oliver Twist", "Charles Dickens", "third_person", "literary"),
    (768, "Wuthering Heights", "Emily Bronte", "first_person", "gothic_romance"),
    (1184, "The Count of Monte Cristo", "Alexandre Dumas", "third_person", "adventure"),
    (2413, "Madame Bovary", "Gustave Flaubert", "third_person", "literary"),
    (514, "Little Women", "Louisa May Alcott", "third_person", "literary"),
    (98, "A Tale of Two Cities", "Charles Dickens", "third_person", "historical"),
    (1232, "The Prince", "Niccolo Machiavelli", "third_person", "philosophy"),
    (46, "A Christmas Carol", "Charles Dickens", "third_person", "literary"),
    (345, "Dracula", "Bram Stoker", "epistolary", "gothic"),
    (84, "Frankenstein", "Mary Shelley", "epistolary", "gothic_sci-fi"),
    (6130, "The Iliad", "Homer", "third_person_omniscient", "epic"),
    (1727, "The Odyssey", "Homer", "third_person_omniscient", "epic"),
    # Omniscient narration
    (2600, "War and Peace", "Leo Tolstoy", "third_person_omniscient", "literary"),
    (145, "Middlemarch", "George Eliot", "third_person_omniscient", "literary"),
    (1023, "Bleak House", "Charles Dickens", "third_person_omniscient", "literary"),
    (599, "Vanity Fair", "William Makepeace Thackeray", "third_person_omniscient", "literary"),
    (135, "Les Misérables", "Victor Hugo", "third_person_omniscient", "literary"),
    (28054, "The Brothers Karamazov", "Fyodor Dostoevsky", "third_person_omniscient", "literary"),
    (1998, "Thus Spake Zarathustra", "Friedrich Nietzsche", "third_person", "philosophy"),
    # Third-person
    (160, "The Awakening", "Kate Chopin", "third_person", "literary"),
    (113, "The Secret Garden", "Frances Hodgson Burnett", "third_person", "literary"),
    (120, "Treasure Island", "Robert Louis Stevenson", "first_person", "adventure"),
    (35, "The Time Machine", "H.G. Wells", "first_person", "sci-fi"),
    (43, "The Strange Case of Dr. Jekyll and Mr. Hyde", "Robert Louis Stevenson", "third_person", "gothic"),
    (1080, "A Modest Proposal", "Jonathan Swift", "first_person", "satire"),
    (16328, "Beowulf", "Anonymous", "third_person_omniscient", "epic"),
    (5230, "The Invisible Man", "H.G. Wells", "third_person", "sci-fi"),
    (215, "The Call of the Wild", "Jack London", "third_person", "adventure"),
    (910, "White Fang", "Jack London", "third_person", "adventure"),
    (1497, "The Republic", "Plato", "first_person", "philosophy"),
    (2591, "Grimms' Fairy Tales", "Brothers Grimm", "third_person_omniscient", "fairy_tale"),
    (27827, "The Kama Sutra", "Vatsyayana", "third_person", "philosophy"),
    (236, "The Jungle Book", "Rudyard Kipling", "third_person_omniscient", "adventure"),
    (1260, "Jane Eyre", "Charlotte Bronte", "first_person", "gothic_romance"),
    # More morally complex works
    (4300, "Ulysses", "James Joyce", "third_person", "literary"),
    (1080, "A Modest Proposal", "Jonathan Swift", "first_person", "satire"),
    (219, "Heart of Darkness", "Joseph Conrad", "first_person", "literary"),
    (203, "Uncle Tom's Cabin", "Harriet Beecher Stowe", "third_person_omniscient", "literary"),
    (74, "The Adventures of Tom Sawyer", "Mark Twain", "third_person", "adventure"),
    (158, "Emma", "Jane Austen", "third_person", "romance"),
    (161, "Sense and Sensibility", "Jane Austen", "third_person", "romance"),
    (105, "Persuasion", "Jane Austen", "third_person", "romance"),
    (1259, "Twenty Thousand Leagues Under the Sea", "Jules Verne", "first_person", "sci-fi"),
    (103, "Around the World in Eighty Days", "Jules Verne", "third_person", "adventure"),
    (45, "Anne of Green Gables", "L.M. Montgomery", "third_person", "literary"),
    (16, "Peter Pan", "J.M. Barrie", "third_person_omniscient", "fantasy"),
    (244, "A Study in Scarlet", "Arthur Conan Doyle", "first_person", "detective"),
    (2097, "The Sign of the Four", "Arthur Conan Doyle", "first_person", "detective"),
    (1513, "Romeo and Juliet", "William Shakespeare", "third_person", "drama"),
    (2229, "The Scarlet Letter", "Nathaniel Hawthorne", "third_person", "literary"),
    (25344, "The Scarlet Pimpernel", "Baroness Orczy", "third_person", "adventure"),
    (164, "The Jungle", "Upton Sinclair", "third_person", "literary"),
    (55, "The Wonderful Wizard of Oz", "L. Frank Baum", "third_person", "fantasy"),
    (779, "The Tragical History of Doctor Faustus", "Christopher Marlowe", "third_person", "drama"),
    (996, "Don Quixote", "Miguel de Cervantes", "third_person_omniscient", "literary"),
    (2814, "Dubliners", "James Joyce", "third_person", "literary"),
    (5740, "Tractatus Logico-Philosophicus", "Ludwig Wittgenstein", "first_person", "philosophy"),
    (1237, "The Phantom of the Opera", "Gaston Leroux", "third_person", "gothic"),
    (829, "Gulliver's Travels", "Jonathan Swift", "first_person", "satire"),
    (62, "A Princess of Mars", "Edgar Rice Burroughs", "first_person", "sci-fi"),
    (69, "Tarzan of the Apes", "Edgar Rice Burroughs", "third_person", "adventure"),
    (3600, "The Art of War", "Sun Tzu", "third_person", "philosophy"),
    (42, "The Strange Case of Dr. Jekyll and Mr. Hyde", "Robert Louis Stevenson", "third_person", "gothic"),
    (940, "The Legend of Sleepy Hollow", "Washington Irving", "third_person", "gothic"),
    (1250, "Anthem", "Ayn Rand", "first_person", "sci-fi"),
    (23, "Narrative of the Life of Frederick Douglass", "Frederick Douglass", "first_person", "autobiography"),
    (5827, "The Problems of Philosophy", "Bertrand Russell", "first_person", "philosophy"),
    (766, "David Copperfield", "Charles Dickens", "first_person", "literary"),
    (2160, "The Importance of Being Earnest", "Oscar Wilde", "third_person", "drama"),
    (4363, "The Gift of the Magi", "O. Henry", "third_person", "literary"),
]


def _safe_filename(title: str) -> str:
    """Convert title to safe filename."""
    safe = re.sub(r'[^\w\s-]', '', title.lower())
    safe = re.sub(r'[\s]+', '_', safe.strip())
    return safe[:60]


def _fetch_url(url: str, retries: int = 3, delay: float = 2.0) -> str:
    """Fetch URL content with retries."""
    headers = {"User-Agent": "AudiobookAgent/1.0 (gutenberg corpus curation)"}
    for attempt in range(retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError) as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt + 1}/{retries} for {url}: {e}")
                time.sleep(delay * (attempt + 1))
            else:
                raise


def _clean_gutenberg_text(text: str) -> str:
    """Strip Gutenberg header/footer boilerplate."""
    # Find start marker
    start_markers = [
        "*** START OF THE PROJECT GUTENBERG",
        "*** START OF THIS PROJECT GUTENBERG",
        "***START OF THE PROJECT GUTENBERG",
    ]
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            # Skip to next line after marker
            nl = text.find("\n", idx)
            if nl != -1:
                text = text[nl + 1:]
            break

    # Find end marker
    end_markers = [
        "*** END OF THE PROJECT GUTENBERG",
        "*** END OF THIS PROJECT GUTENBERG",
        "***END OF THE PROJECT GUTENBERG",
        "End of the Project Gutenberg",
        "End of Project Gutenberg",
    ]
    for marker in end_markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
            break

    return text.strip()


def _download_text(gutenberg_id: int) -> str | None:
    """Download text from Gutenberg mirrors."""
    # Try plain text URLs in order of reliability
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}.txt",
    ]

    for url in urls:
        try:
            text = _fetch_url(url)
            if len(text) > 1000:  # Sanity check
                return _clean_gutenberg_text(text)
        except Exception:
            continue

    return None


def curate():
    """Download and catalog all curated books."""
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    # Deduplicate by gutenberg_id
    seen_ids = set()
    unique_books = []
    for book in CURATED_BOOKS:
        gid = book[0]
        if gid not in seen_ids:
            seen_ids.add(gid)
            unique_books.append(book)

    print(f"Curated list: {len(unique_books)} unique books (from {len(CURATED_BOOKS)} entries)")
    print(f"Output dir: {CORPUS_DIR}")
    print()

    metadata = {}
    success = 0
    failed = []

    for i, (gid, title, author, expected_pov, genre) in enumerate(unique_books):
        filename = f"{_safe_filename(title)}.txt"
        filepath = CORPUS_DIR / filename

        # Skip if already downloaded
        if filepath.exists() and filepath.stat().st_size > 1000:
            print(f"[{i+1}/{len(unique_books)}] SKIP (exists): {title}")
            metadata[filename] = {
                "title": title,
                "author": author,
                "gutenberg_id": gid,
                "expected_pov": expected_pov,
                "genre": genre,
                "char_count": filepath.stat().st_size,
            }
            success += 1
            continue

        print(f"[{i+1}/{len(unique_books)}] Downloading: {title} (ID: {gid})...", end=" ")
        sys.stdout.flush()

        text = _download_text(gid)
        if text and len(text) > 5000:
            filepath.write_text(text, encoding="utf-8")
            metadata[filename] = {
                "title": title,
                "author": author,
                "gutenberg_id": gid,
                "expected_pov": expected_pov,
                "genre": genre,
                "char_count": len(text),
            }
            print(f"OK ({len(text):,} chars)")
            success += 1
        else:
            print("FAILED (too short or unavailable)")
            failed.append((gid, title))

        # Be polite to Gutenberg servers
        time.sleep(1.0)

    # Save metadata
    meta_path = CORPUS_DIR / "corpus_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    print(f"Corpus curation complete")
    print(f"  Downloaded: {success}/{len(unique_books)}")
    print(f"  Failed: {len(failed)}")
    if failed:
        for gid, title in failed:
            print(f"    - {title} (ID: {gid})")

    # POV distribution
    pov_counts = {}
    genre_counts = {}
    for m in metadata.values():
        pov = m["expected_pov"]
        genre = m["genre"]
        pov_counts[pov] = pov_counts.get(pov, 0) + 1
        genre_counts[genre] = genre_counts.get(genre, 0) + 1

    print(f"\n  POV distribution:")
    for pov, count in sorted(pov_counts.items()):
        print(f"    {pov}: {count}")

    print(f"\n  Genre distribution:")
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1]):
        print(f"    {genre}: {count}")

    print(f"\n  Metadata: {meta_path}")
    print(f"  Corpus dir: {CORPUS_DIR}")


if __name__ == "__main__":
    curate()
