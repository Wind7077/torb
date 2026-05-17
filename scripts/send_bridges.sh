#!/bin/bash
set -euo pipefail

# ============================================
# File with bridges
# ============================================

FILE="webtunnel.txt"

# ============================================
# Check ENV variables
# ============================================

if [[ -z "${BOT_TOKEN:-}" ]]; then
  echo "ERROR: BOT_TOKEN is not set"
  exit 1
fi

if [[ -z "${CHAT_ID:-}" ]]; then
  echo "ERROR: CHAT_ID is not set"
  exit 1
fi

# ============================================
# Counters
# ============================================

COUNT=$(grep -c '^webtunnel ' "$FILE" || true)
SNI_COUNT=$(grep -c 'sni-imitation=' "$FILE" || true)

# ============================================
# Send Telegram message
# ============================================

send_msg() {
  local text="$1"

  curl -fsS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    -d parse_mode="HTML" \
    -d disable_web_page_preview="true" \
    --data-urlencode "text=${text}" \
    > /dev/null

  sleep 0.5
}

# ============================================
# Clean line for Tor VPN Beta
# Removes:
# - CRLF
# - sni-imitation
# ============================================

clean_for_torvpn() {
  local line="$1"

  # remove CRLF
  line="${line//$'\r'/}"

  # remove sni-imitation=...
  line=$(echo "$line" | sed -E 's/ sni-imitation=[^ ]+//g')

  echo "$line"
}

# ============================================
# Clean RAW SNI line
# - keep sni-imitation
# - remove www.
# ============================================

clean_raw_sni() {
  local line="$1"

  # remove CRLF
  line="${line//$'\r'/}"

  # remove all www.
  line="${line//www./}"

  echo "$line"
}

# ============================================
# Send PRE block
# ============================================

send_block() {
  local text="$1"

  send_msg "<pre><code>${text}</code></pre>"
}

# ============================================
# Header
# ============================================

send_msg "🧅 WEBTUNNEL bridges — ${COUNT} шт.
⭐ SNI bridges: ${SNI_COUNT} шт.
🕐 $(date -u '+%Y-%m-%d %H:%M UTC')"

# ============================================
# SECTION 1
# Compatible with Tor VPN Beta
# ============================================

send_msg "✅ Tor VPN Beta compatible bridges:"

i=0
chunk=""

while IFS= read -r line; do

  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue

  line=$(clean_for_torvpn "$line")

  if [ $i -eq 0 ]; then
    chunk="$line"
  else
    chunk+=$'\n'"$line"
  fi

  i=$((i + 1))

  if [ $i -eq 15 ]; then
    send_block "$chunk"

    chunk=""
    i=0
  fi

done < <(grep '^webtunnel ' "$FILE")

[[ -n "$chunk" ]] && send_block "$chunk"

# ============================================
# SECTION 2
# RAW SNI bridges
# ============================================

if [ "$SNI_COUNT" -gt 0 ]; then

  send_msg "⭐ RAW bridges with sni-imitation (for clients that support it):"

  i=0
  chunk=""

  while IFS= read -r line; do

    [[ -z "$line" ]] && continue

    line=$(clean_raw_sni "$line")

    if [ $i -eq 0 ]; then
      chunk="$line"
    else
      chunk+=$'\n'"$line"
    fi

    i=$((i + 1))

    if [ $i -eq 10 ]; then
      send_block "$chunk"

      chunk=""
      i=0
    fi

  done < <(grep 'sni-imitation=' "$FILE")

  [[ -n "$chunk" ]] && send_block "$chunk"
fi

# ============================================
# Done
# ============================================

send_msg "✅ Готово! Отправлено: ${COUNT} bridges."
