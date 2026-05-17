#!/bin/bash
set -euo pipefail

COUNT=$(grep -c '^webtunnel ' webtunnel.txt || true)
SNI_COUNT=$(grep -c 'sni-imitation' webtunnel.txt || true)

send_msg() {
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    -d parse_mode="HTML" \
    -d disable_web_page_preview="true" \
    --data-urlencode "text=$1"
  sleep 0.5
}

send_block() {
  # Каждый мост в отдельном <code> — не кликабельно, копируется чисто
  local lines="$1"
  local text=""
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    text="${text}<code>${line}</code>"$'\n'
  done <<< "$lines"
  send_msg "$text"
}

# Заголовок
send_msg "🧅 WEBTUNNEL bridges — ${COUNT} шт.
⭐ С SNI-imitation: ${SNI_COUNT} шт.
🕐 $(date -u '+%Y-%m-%d %H:%M UTC')"

# SNI bridges — первыми
if [ "$SNI_COUNT" -gt 0 ]; then
  send_msg "⭐ Bridges с SNI-imitation:"
  i=0
  chunk=""
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if [ $i -eq 0 ]; then
      chunk="$line"
    else
      chunk="${chunk}"$'\n'"$line"
    fi
    i=$((i+1))
    if [ $i -eq 10 ]; then
      send_block "$chunk"
      chunk=""
      i=0
    fi
  done < <(grep 'sni-imitation' webtunnel.txt)
  [ -n "$chunk" ] && send_block "$chunk"
fi

# Остальные bridges
send_msg "🌐 Остальные webtunnel bridges:"
i=0
chunk=""
while IFS= read -r line; do
  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue
  [[ "$line" == *"sni-imitation"* ]] && continue
  if [ $i -eq 0 ]; then
    chunk="$line"
  else
    chunk="${chunk}"$'\n'"$line"
  fi
  i=$((i+1))
  if [ $i -eq 15 ]; then
    send_block "$chunk"
    chunk=""
    i=0
  fi
done < <(grep '^webtunnel ' webtunnel.txt)
[ -n "$chunk" ] && send_block "$chunk"

send_msg "✅ Готово! Отправлено: ${COUNT} bridges."
