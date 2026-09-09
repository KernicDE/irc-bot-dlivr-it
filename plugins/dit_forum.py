"""
Forum-RSS-Polling für den IRC-Bot.
Postet neue Diskussionen aus den Tags news, applications und public in #dlivr.
"""
import os
import sqlite3
import threading
import time

import feedparser
from sopel import module

IRC_CHANNEL = "#dlivr"
DB_PATH = "/bot/data/seen_entries.sqlite"
FEEDS = {
    "news": "https://dlivr.it/atom/t/news",
    "applications": "https://dlivr.it/atom/t/applications",
    "public": "https://dlivr.it/atom/t/public",
}
POLL_INTERVAL = 60  # Sekunden


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_entries (
            feed TEXT NOT NULL,
            entry_id TEXT NOT NULL,
            title TEXT,
            link TEXT,
            published TEXT,
            PRIMARY KEY (feed, entry_id)
        )
    """)
    conn.commit()
    conn.close()


def _is_seen(feed, entry_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT 1 FROM seen_entries WHERE feed = ? AND entry_id = ?",
        (feed, entry_id),
    )
    seen = cur.fetchone() is not None
    conn.close()
    return seen


def _mark_seen(feed, entry_id, title, link, published):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO seen_entries (feed, entry_id, title, link, published) VALUES (?, ?, ?, ?, ?)",
        (feed, entry_id, title, link, published),
    )
    conn.commit()
    conn.close()


def _poll_feed(bot, feed_name, feed_url):
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as exc:
        bot.say(f"[Forum] RSS-Fehler {feed_name}: {exc}", IRC_CHANNEL)
        return

    for entry in parsed.entries:
        entry_id = entry.get("id") or entry.get("link")
        if not entry_id:
            continue
        if _is_seen(feed_name, entry_id):
            continue
        title = entry.get("title", "Neuer Beitrag")
        link = entry.get("link", feed_url)
        published = entry.get("published", "")
        _mark_seen(feed_name, entry_id, title, link, published)
        bot.say(f"[Forum /{feed_name}] {title} | {link}", IRC_CHANNEL)


def _poll_loop(bot):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _init_db()
    while True:
        for feed_name, feed_url in FEEDS.items():
            _poll_feed(bot, feed_name, feed_url)
        time.sleep(POLL_INTERVAL)


@module.event('001')
@module.event('376')
def start_forum_polling(bot, trigger):
    if "forum_poll_thread" not in bot.memory:
        thread = threading.Thread(target=_poll_loop, args=(bot,), daemon=True)
        thread.start()
        bot.memory["forum_poll_thread"] = thread
