from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import time
import json

import requests
from bs4 import BeautifulSoup


START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/Dexterkwokch)"
}


def fetch_page(url, cache_file):
    # Use the cached page if we already downloaded it
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT: {url}")
        return html

    # Otherwise, request the page from the website
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    # Only HTTP 200 is considered successful
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    # Create the cache directory if necessary
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    # Save the downloaded HTML
    cache_file.write_bytes(response.content)

    print(f"FETCH: {url}")

    # Be polite to the website
    time.sleep(0.5)

    return response.text


def extract_book(html, product_url, source_page):
    soup = BeautifulSoup(html, "html.parser")

    # Focus on the product area instead of searching the whole page
    product = soup.select_one("article.product_page")

    # Title
    title = product.select_one(
        "div.product_main h1"
    ).get_text(strip=True)

    # Raw price, e.g. £51.77
    price_text = product.select_one(
        "div.product_main p.price_color"
    ).get_text(strip=True)

    # Availability, e.g. In stock (22 available)
    availability_text = product.select_one(
        "div.product_main p.availability"
    ).get_text(" ", strip=True)

    # Rating is stored in the HTML class:
    # <p class="star-rating Three">
    rating_element = product.select_one(
        "div.product_main p.star-rating"
    )

    rating_text = rating_element["class"][1]

    # Description is optional
    description_heading = product.find(
        "div",
        id="product_description"
    )

    if description_heading:
        description_element = description_heading.find_next_sibling("p")

        if description_element:
            description = description_element.get_text(" ", strip=True)
        else:
            description = None
    else:
        description = None

    # Record when we collected the data
    fetched_at = (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


# --------------------------------------------------
# Stage 2: Discover books from first 3 catalogue pages
# --------------------------------------------------

discovered_books = []

page_url = START_URL
catalogue_pages = 0

while page_url and catalogue_pages < 3:

    catalogue_pages += 1

    cache_file = Path(
        f"cache/catalogue-page-{catalogue_pages}.html"
    )

    html = fetch_page(page_url, cache_file)

    soup = BeautifulSoup(html, "html.parser")

    books = soup.select("article.product_pod")

    for book in books:
        link = book.select_one("h3 a")

        if link:
            book_url = urljoin(
                page_url,
                link["href"]
            )

            # Remember both the book URL and where we found it
            discovered_books.append({
                "product_url": book_url,
                "source_page": page_url
            })

    # Follow the website's own "next" link
    next_link = soup.select_one("li.next a")

    if next_link:
        page_url = urljoin(
            page_url,
            next_link["href"]
        )
    else:
        page_url = None


# --------------------------------------------------
# Remove duplicate book URLs
# --------------------------------------------------

unique_books_dict = {}

for book in discovered_books:
    unique_books_dict[book["product_url"]] = book

unique_books = list(unique_books_dict.values())


print(f"catalogue_pages={catalogue_pages}")
print(f"discovered={len(discovered_books)}")
print(f"unique_urls={len(unique_books)}")


# --------------------------------------------------
# Stage 3: Visit and extract all 60 book pages
# --------------------------------------------------

raw_records = []

for i, book in enumerate(unique_books, start=1):

    product_url = book["product_url"]
    source_page = book["source_page"]

    # Each book gets its own cached HTML file
    cache_file = Path(
        f"cache/books/book-{i}.html"
    )

    html = fetch_page(
        product_url,
        cache_file
    )

    record = extract_book(
        html,
        product_url,
        source_page
    )

    raw_records.append(record)


# --------------------------------------------------
# Stage 3 checkpoint
# --------------------------------------------------

# Print one complete raw record
if raw_records:
    print("\nExample raw record:")

    print(
        json.dumps(
            raw_records[0],
            indent=2,
            ensure_ascii=False
        )
    )

print(f"\ndetail_pages={len(raw_records)}")