name: Send Bridges to Telegram

on:
  workflow_dispatch:

jobs:
  send:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Download webtunnel bridges
        run: |
          curl -fsSL \
            "https://raw.githubusercontent.com/Delta-Kronecker/Tor-Bridges-Collector/main/bridge/webtunnel_tested.txt" \
            -o webtunnel.txt

      - name: Send to Telegram
        env:
          BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          CHAT_ID: ${{ secrets.TG_CHAT_ID }}
        run: bash scripts/send_bridges.sh
