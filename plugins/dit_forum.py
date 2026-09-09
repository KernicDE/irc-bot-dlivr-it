"""
Forum-RSS-Polling für den IRC-Bot.
Postet neue Diskussionen aus dem globalen, unauthentifizierten Feed in #dlivr.
Da der Feed ohne Login abgerufen wird, enthält er automatisch genau die
Diskussionen, die auch ein Gast ohne Anmeldung sehen könnte - unabhängig
davon, welche Tags gerade wie eingeschränkt sind.
"""
import os
import sqlite3
import threading
import time

import feedparser
from sopel import module

IRC_CHANNEL = "#dlivr"
DB_PATH = "/bot/data/seen_entries.sqlite"
FEED_NAME = "all"
FEED_URL = "https://dlivr.it/atom"
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


def _poll_feed(bot):
    try:
        parsed = feedparser.parse(FEED_URL)
    except Exception as exc:
        # Nicht per bot.say melden: Ein dauerhafter Fehler würde sonst bei
        # jedem Poll-Intervall (60s) erneut in den Channel spammen.
        print(f"[dit_forum] RSS-Fehler beim Abruf von {FEED_URL}: {exc}")
        return

    for entry in parsed.entries:
        entry_id = entry.get("id") or entry.get("link")
        if not entry_id:
            continue
        if _is_seen(FEED_NAME, entry_id):
            continue

        title = entry.get("title", "Neuer Beitrag")
        link = entry.get("link", FEED_URL)
        published = entry.get("published", "")

        # Erst posten, dann als gesehen markieren - schlägt bot.say fehl
        # (z.B. kurzer IRC-Disconnect), bleibt der Eintrag offen und wird
        # beim nächsten Poll erneut versucht, statt für immer verloren zu
        # gehen.
        try:
            bot.say(f"[Forum] {title} | {link}", IRC_CHANNEL)
        except Exception as exc:
            print(f"[dit_forum] Konnte Eintrag nicht posten, versuche es beim nächsten Poll erneut: {exc}")
            continue

        _mark_seen(FEED_NAME, entry_id, title, link, published)


def _poll_loop(bot):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _init_db()
    while True:
        try:
            _poll_feed(bot)
        except Exception as exc:
            # Ohne dieses Netz würde eine einzelne unerwartete Exception den
            # kompletten Poll-Thread lautlos für immer beenden (Container
            # läuft weiter, es wird aber nie wieder gepollt).
            print(f"[dit_forum] Unerwarteter Fehler im Poll-Loop, mache beim nächsten Intervall weiter: {exc}")
        time.sleep(POLL_INTERVAL)


@module.event('001')
@module.event('376')
def start_forum_polling(bot, trigger):
    if "forum_poll_thread" not in bot.memory:
        thread = threading.Thread(target=_poll_loop, args=(bot,), daemon=True)
        thread.start()
        bot.memory["forum_poll_thread"] = thread
