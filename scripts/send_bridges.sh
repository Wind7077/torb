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
# ============================================

normalize_bridge() {
  local line="$1"

  # remove CRLF
  line="${line//$'\r'/}"

  # process sni-imitation
  if [[ "$line" =~ sni-imitation=([^[:space:]]+) ]]; then

    sni_list="${BASH_REMATCH[1]}"

    # first domain only
    first_sni="${sni_list%%,*}"

    # remove www.
    first_sni="${first_sni#www.}"

    # replace whole sni-imitation field
    line=$(echo "$line" | sed -E \
      "s/sni-imitation=[^ ]+/sni-imitation=${first_sni}/")
  fi

  echo "$line"
}

# ============================================
# Send bridges block
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
🕐 $(date -u '+%Y-%m-%d %H:%M UTC')"

# ============================================
# Send bridges
# ============================================

i=0
chunk=""

while IFS= read -r line; do

  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue

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
