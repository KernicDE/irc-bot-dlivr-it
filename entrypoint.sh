#!/bin/bash
set -e

NICKSERV_PASSWORD="${NICKSERV_PASSWORD:-}"

if [ -z "$NICKSERV_PASSWORD" ]; then
    echo "WARNUNG: NICKSERV_PASSWORD ist nicht gesetzt. Der Bot kann sich nicht bei NickServ identifizieren." >&2
fi

# Stelle sicher, dass data-Verzeichnisse existieren und nobody beschreiben kann
mkdir -p /bot/data/logs
chown -R nobody:nogroup /bot/data 2>/dev/null || true

# Stale PID-Datei von einem harten Container-Neustart/Crash entfernen -
# es läuft ohnehin immer nur eine Instanz pro Container, ein Lockfile-Leichnam
# darf den nächsten Start nicht blockieren.
rm -f /bot/data/*.pid

# sopel.cfg aus Template mit Passwort generieren
rm -f /tmp/sopel.cfg
sed "s|\\\${NICKSERV_PASSWORD}|${NICKSERV_PASSWORD}|g" /bot/sopel.cfg.template > /tmp/sopel.cfg
chown nobody:nogroup /tmp/sopel.cfg

exec setpriv --reuid=nobody --regid=nogroup --clear-groups "$@" -c /tmp/sopel.cfg
