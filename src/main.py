from pathlib import Path
from urllib.parse import urljoin
import time

import requests
from bs4 import BeautifulSoup


START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/Dexterkwokch)"
}


def fetch_page(url, cache_file):
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        print(f"CACHE HIT: {url}")
        return html

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(response.content)

    print(f"FETCH: {url}")

    time.sleep(0.5)

    return response.text


book_urls = []
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
            book_url = urljoin(page_url, link["href"])
            book_urls.append(book_url)

    next_link = soup.select_one("li.next a")

    if next_link:
        page_url = urljoin(page_url, next_link["href"])
    else:
        page_url = None


unique_urls = list(dict.fromkeys(book_urls))


print(f"catalogue_pages={catalogue_pages}")
print(f"discovered={len(book_urls)}")
print(f"unique_urls={len(unique_urls)}")