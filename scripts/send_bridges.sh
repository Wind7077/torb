#!/bin/bash
set -euo pipefail

COUNT=$(grep -c '^webtunnel ' webtunnel.txt || true)
SNI_COUNT=$(grep -c 'sni-imitation' webtunnel.txt || true)

send_msg() {
  curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    -d parse_mode="Markdown" \
    --data-urlencode "text=$1"
  sleep 0.5
}

send_block() {
  local lines="$1"
  local text
  text=$(printf '```\n%s\n```' "$lines")
  send_msg "$text"
}

# Заголовок
send_msg "🧅 *WEBTUNNEL bridges* — ${COUNT} шт.
⭐ С SNI-imitation: ${SNI_COUNT} шт.
🕐 $(date -u '+%Y-%m-%d %H:%M UTC')

_Нажми Copy на блоке — скопируются все мосты сразу_
_Блоки ⭐ SNI лучше обходят белые списки РФ_"

# SNI bridges — первыми
SNI_LINES=$(grep 'sni-imitation' webtunnel.txt || true)
if [ -n "$SNI_LINES" ]; then
  send_msg "⭐ *Bridges с SNI-imitation:*"
  i=0
  chunk=""
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    chunk="${chunk}${line}"$'\n'
    i=$((i+1))
    if [ $i -eq 10 ]; then
      send_block "${chunk%$'\n'}"
      chunk=""
      i=0
    fi
  done <<< "$SNI_LINES"
  [ -n "$chunk" ] && send_block "${chunk%$'\n'}"
fi

# Остальные bridges
send_msg "🌐 *Остальные webtunnel bridges:*"
i=0
chunk=""
while IFS= read -r line; do
  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue
  [[ "$line" == *"sni-imitation"* ]] && continue
  chunk="${chunk}${line}"$'\n'
  i=$((i+1))
  if [ $i -eq 15 ]; then
    send_block "${chunk%$'\n'}"
    chunk=""
    i=0
  fi
done < <(grep '^webtunnel ' webtunnel.txt)
[ -n "$chunk" ] && send_block "${chunk%$'\n'}"

send_msg "✅ Готово! Отправлено: ${COUNT} bridges."
