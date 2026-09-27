from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime, timezone
import time
import json
from pydantic import BaseModel, HttpUrl, ValidationError

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


class Book(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: HttpUrl
    fetched_at: str


def normalize_price(price_text):
    return float(price_text.replace("£", ""))


START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/Dexterkwokch)"
}


def fetch_page(url, cache_file):
    global pages_fetched, cache_hits

    # Use cache if available
    if cache_file.exists():
        cache_hits += 1

        html = cache_file.read_text(encoding="utf-8")

        print(f"CACHE HIT: {url}")

        return html

    # Maximum of 2 attempts:
    # first request + one retry
    for attempt in range(2):

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            pages_fetched += 1

        except requests.exceptions.Timeout:

            if attempt == 0:
                print(f"TIMEOUT: {url} - retrying once...")
                time.sleep(1)
                continue

            raise RuntimeError(
                f"Request timed out after retry: {url}"
            )

        # Success
        if response.status_code == 200:

            cache_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            cache_file.write_bytes(
                response.content
            )

            print(f"FETCH: {url}")

            time.sleep(0.5)

            return response.text

        # Do NOT retry 404 or 403
        if response.status_code in (403, 404):
            raise RuntimeError(
                f"HTTP {response.status_code}: {url}"
            )

        # Retry a server error once
        if 500 <= response.status_code < 600:

            if attempt == 0:
                print(
                    f"HTTP {response.status_code}: "
                    f"{url} - retrying once..."
                )

                time.sleep(1)
                continue

            raise RuntimeError(
                f"HTTP {response.status_code} after retry: {url}"
            )

        # Other HTTP errors
        raise RuntimeError(
            f"HTTP {response.status_code}: {url}"
        )


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
unique_books.append({
    "product_url": "https://books.toscrape.com/catalogue/this-book-does-not-exist-99999/index.html",
    "source_page": "TEST"
})


print(f"catalogue_pages={catalogue_pages}")
print(f"discovered={len(discovered_books)}")
print(f"unique_urls={len(unique_books)}")


# --------------------------------------------------
# Stage 3: Visit and extract all 60 book pages
# --------------------------------------------------

raw_records = []
page_failures = []

for i, book in enumerate(unique_books, start=1):

    product_url = book["product_url"]
    source_page = book["source_page"]

    cache_file = Path(
        f"cache/books/book-{i}.html"
    )

    try:
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

    except Exception as error:
        failed_pages += 1

        page_failures.append({
            "url": product_url,
            "reason": str(error)
        })

        print(
            f"SKIPPED: {product_url} "
            f"({error})"
        )


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


def normalize_price(price_text):
    return float(price_text.replace("£", ""))


# --------------------------------------------------
# Stage 4: Normalize and validate records
# --------------------------------------------------

valid_records = []
errors = []

for raw_record in raw_records:

    try:
        finished_record = {
            **raw_record,
            "price_gbp": normalize_price(
                raw_record["price_text"]
            )
        }

        book = Book(**finished_record)

        valid_records.append(
            book.model_dump(mode="json")
        )

    except (ValidationError, ValueError) as error:
        errors.append({
            "product_url": raw_record.get("product_url"),
            "reason": str(error)
        })


# --------------------------------------------------
# Remove duplicates using canonical product URL
# --------------------------------------------------

unique_records = {}

for record in valid_records:
    unique_records[record["product_url"]] = record

valid_records = list(unique_records.values())


# --------------------------------------------------
# Store output
# --------------------------------------------------

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


with open(
    OUTPUT_DIR / "books.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        valid_records,
        file,
        indent=2,
        ensure_ascii=False
    )


with open(
    OUTPUT_DIR / "errors.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        errors,
        file,
        indent=2,
        ensure_ascii=False
    )

run_finished = datetime.now(timezone.utc)

duration_seconds = (
    run_finished - run_started
).total_seconds()

run_report = {
    "start_time": run_started.isoformat().replace("+00:00", "Z"),
    "duration_seconds": round(duration_seconds, 2),
    "pages_fetched": pages_fetched,
    "cache_hits": cache_hits,
    "valid_records": len(valid_records),
    "invalid_records": len(errors),
    "failed_pages": failed_pages,
    "failures": page_failures
}

with open(
    OUTPUT_DIR / "run-report.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        run_report,
        file,
        indent=2,
        ensure_ascii=False
    )


print(f"valid_records={len(valid_records)}")
print(f"invalid_records={len(errors)}")