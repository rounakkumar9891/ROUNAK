from flask import Flask, request, render_template, jsonify
import sqlite3
import threading
import time
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

APP_NAME = "ROUNAK"
SITE_URL = "https://rounakkumar.com"
DB = "rounak.db"
USER_AGENT = "ROUNAKBot/1.0"

app = Flask(__name__)

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
            url UNINDEXED,
            title,
            body,
            tokenize='unicode61'
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS crawl_queue(
            url TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            added_at REAL
        )
    """)
    con.commit()
    con.close()

def add_url(url):
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            return False
        con = db()
        con.execute(
            "INSERT OR IGNORE INTO crawl_queue(url, status, added_at) VALUES (?, 'pending', ?)",
            (url, time.time())
        )
        con.commit()
        con.close()
        return True
    except Exception:
        return False

def allowed_by_robots(url):
    try:
        p = urlparse(url)
        robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
        rp = RobotFileParser(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True

def index_page(url, html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else url
    body = soup.get_text(" ", strip=True)
    body = " ".join(body.split())

    if len(body) < 30:
        return []

    con = db()
    con.execute("DELETE FROM pages WHERE url = ?", (url,))
    con.execute("INSERT INTO pages(url, title, body) VALUES (?, ?, ?)",
                (url, title[:500], body[:200000]))
    con.commit()
    con.close()

    links = []
    p = urlparse(url)
    for a in soup.find_all("a", href=True):
        nxt = urljoin(url, a["href"]).split("#")[0]
        q = urlparse(nxt)
        if q.scheme in ("http", "https") and q.netloc:
            links.append(nxt)
    return list(dict.fromkeys(links))

def crawl_once():
    con = db()
    row = con.execute(
        "SELECT url FROM crawl_queue WHERE status='pending' ORDER BY added_at LIMIT 1"
    ).fetchone()
    if not row:
        con.close()
        return False

    url = row["url"]
    con.execute("UPDATE crawl_queue SET status='working' WHERE url=?", (url,))
    con.commit()
    con.close()

    try:
        if not allowed_by_robots(url):
            raise RuntimeError("robots.txt disallowed")

        r = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True
        )
        ctype = r.headers.get("content-type", "")
        if r.ok and "text/html" in ctype:
            final_url = r.url
            links = index_page(final_url, r.text)
            for link in links[:100]:
                add_url(link)

        status = "done"
    except Exception:
        status = "error"

    con = db()
    con.execute("UPDATE crawl_queue SET status=? WHERE url=?", (status, url))
    con.commit()
    con.close()
    return True

def crawler_loop():
    while True:
        did = crawl_once()
        if not did:
            time.sleep(2)

@app.route("/")
def home():
    return render_template("index.html", app_name=APP_NAME, site_url=SITE_URL)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"query": "", "results": []})

    # FTS5 query: split user input into safe tokens and search all tokens.
    tokens = [x.replace('"', ' ').strip() for x in q.split() if x.strip()]
    fts = " AND ".join(f'"{x}"' for x in tokens[:12])

    con = db()
    rows = con.execute("""
        SELECT url, title,
               snippet(pages, 2, '<mark>', '</mark>', ' … ', 35) AS snippet,
               bm25(pages) AS rank
        FROM pages
        WHERE pages MATCH ?
        ORDER BY rank
        LIMIT 30
    """, (fts,)).fetchall()
    con.close()

    return jsonify({
        "query": q,
        "results": [dict(r) for r in rows]
    })

@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(silent=True) or {}
    urls = data.get("urls", [])
    if isinstance(urls, str):
        urls = [urls]

    added = sum(add_url(u.strip()) for u in urls if isinstance(u, str) and u.strip())
    return jsonify({"added": added})

@app.route("/stats")
def stats():
    con = db()
    pages = con.execute("SELECT count(*) FROM pages").fetchone()[0]
    pending = con.execute(
        "SELECT count(*) FROM crawl_queue WHERE status='pending'"
    ).fetchone()[0]
    con.close()
    return jsonify({"pages": pages, "pending": pending})

if __name__ == "__main__":
    init_db()
    threading.Thread(target=crawler_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
