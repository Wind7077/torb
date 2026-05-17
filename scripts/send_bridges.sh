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
SNI_COUNT=$(grep -c 'sni-imitation' "$FILE" || true)

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
# Normalize bridge line
# Removes ALL www.
# ============================================

normalize_bridge() {
  local line="$1"

  # remove CRLF
  line="${line//$'\r'/}"

  # remove all www.
  line="${line//www./}"

  echo "$line"
}

# ============================================
# Send bridges block
# One PRE block = one Copy Code button
# ============================================

send_block() {
  local lines="$1"

  local cleaned=""

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue

    line=$(normalize_bridge "$line")

    cleaned+="${line}"$'\n'
  done <<< "$lines"

  send_msg "<pre><code>${cleaned}</code></pre>"
}

# ============================================
# Header
# ============================================

send_msg "🧅 WEBTUNNEL bridges — ${COUNT} шт.
⭐ С SNI-imitation: ${SNI_COUNT} шт.
🕐 $(date -u '+%Y-%m-%d %H:%M UTC')"

# ============================================
# Send SNI bridges first
# ============================================

if [ "$SNI_COUNT" -gt 0 ]; then

  send_msg "⭐ Bridges с SNI-imitation:"

  i=0
  chunk=""

  while IFS= read -r line; do

    [[ -z "$line" ]] && continue

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

  done < <(grep 'sni-imitation' "$FILE")

  [[ -n "$chunk" ]] && send_block "$chunk"
fi

# ============================================
# Send remaining bridges
# ============================================

send_msg "🌐 Остальные WEBTUNNEL bridges:"

i=0
chunk=""

while IFS= read -r line; do

  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue
  [[ "$line" == *"sni-imitation"* ]] && continue

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
# Done
# ============================================

send_msg "✅ Готово! Отправлено: ${COUNT} bridges."
