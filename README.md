# The Polite Scraper

A small web scraping project built as part of the FlyRank Backend Development Internship.

The scraper collects book information from the first three catalogue pages of Books to Scrape. It discovers 60 books, visits each book page, extracts the required data, validates it, and stores the results as JSON.

## Target Classification

- **Target:** Books to Scrape
- **Purpose:** The website is a sandbox designed for practising web scraping.
- **Scope:** Only the first 3 catalogue pages (60 books).
- **Data collected:** title, product URL, price, availability, rating, description, source page, and fetch time.
- **robots.txt:** No robots file found (HTTP 404).
- **Why this is appropriate:** Books to Scrape is specifically provided as a practice website for web scraping.

I will not reuse this code on another site without checking its rules and terms first.

## Tech Stack

I used the Python lane for this assignment.

- Python 3
- Requests
- Beautiful Soup
- Pydantic

Requests is used to download pages, Beautiful Soup is used to parse the HTML, and Pydantic validates the final records before they are stored.

## Installation

Clone the repository and enter the project directory:

```bash
git clone <YOUR-REPOSITORY-URL>
cd <YOUR-REPOSITORY-NAME>