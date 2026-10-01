# ROUNAK Search Engine

Public website: https://rounakkumar.com

ROUNAK is a self-hosted web search engine starter. It stores crawled pages in a local SQLite FTS5 index and searches that index quickly.

## 1. Install

Python 3.10+ recommended.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

## 2. Run

```bash
python app.py
```

Open:

http://127.0.0.1:5000

## 3. Add data

Enter a website such as:

https://example.com

ROUNAK will queue it, download allowed HTML pages, extract text, store the pages locally, discover links, and continue crawling.

## Important

ROUNAK does not contain the entire internet by default. No practical single project can ship with "all internet data". The crawler builds the index over time.

Respect website terms, robots.txt, copyright, rate limits, and applicable laws. Only crawl sites you are allowed to crawl.

## Next upgrades

- distributed crawling
- language detection
- spelling correction
- autocomplete
- image/news indexes
- ranking signals
- duplicate detection
- per-domain crawl limits
- sitemap support
- HTTPS deployment
- admin dashboard
- API keys and abuse protection
