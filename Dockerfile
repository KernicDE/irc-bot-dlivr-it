# pymumble_py3 1.6.1 ruft noch ssl.wrap_socket() auf, das in Python 3.12
# entfernt wurde (deprecated seit 3.7). 3.11 ist die letzte Version, die
# es noch hat - siehe https://docs.python.org/3.12/whatsnew/3.12.html.
FROM python:3.11-slim

WORKDIR /bot

# libopus0: pymumble_py3 nutzt opuslib, das zur Laufzeit gegen die native
# libopus-Bibliothek linkt - ohne die schlägt schon der Import fehl.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libopus0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir sopel pymumble feedparser

COPY entrypoint.sh /bot/entrypoint.sh
COPY sopel.cfg.template /bot/sopel.cfg.template
COPY plugins /bot/plugins

RUN chmod +x /bot/entrypoint.sh

# Container startet als root, entrypoint wechselt dann zu nobody
ENTRYPOINT ["/bot/entrypoint.sh"]
CMD ["sopel", "-c", "/bot/sopel.cfg"]
