#!/bin/bash
# =============================================================
# check_bridges.sh — проверяет obfs4 и webtunnel bridges через tor
#
# Использование:
#   bash check_bridges.sh <bridges_file> <transport> <output_file>
#
# Примеры:
#   bash check_bridges.sh raw_obfs4.txt     obfs4     working_obfs4.txt
#   bash check_bridges.sh raw_webtunnel.txt webtunnel working_webtunnel.txt
# =============================================================

set -euo pipefail

BRIDGES_FILE="${1:?Укажи файл с bridges}"
TRANSPORT="${2:?Укажи тип транспорта: obfs4 или webtunnel}"
OK_FILE="${3:?Укажи выходной файл}"

TOR_TIMEOUT=25   # секунд ждать bootstrap
MAX_PARALLEL=5   # параллельных tor-процессов

> "$OK_FILE"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ---------- читаем строки нужного транспорта ----------
mapfile -t BRIDGES < <(grep -E "^${TRANSPORT} " "$BRIDGES_FILE" || true)
TOTAL=${#BRIDGES[@]}

echo -e "${YELLOW}🔍 [$TRANSPORT] Bridges для проверки: $TOTAL${NC}"
echo -e "${YELLOW}⚡ Параллельность: $MAX_PARALLEL | Таймаут: ${TOR_TIMEOUT}s${NC}"
echo "────────────────────────────────────────────────"

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${RED}⚠️  Не найдено bridges типа '$TRANSPORT' в файле $BRIDGES_FILE${NC}"
    exit 0
fi

# ---------- проверка одного bridge ----------
check_one() {
    local bridge_line="$1"
    local idx="$2"
    local transport="$3"
    local ok_file="$4"
    local timeout_sec="$5"

    local workdir
    workdir=$(mktemp -d)

    local socks_port=$((19050 + idx))
    local control_port=$((19150 + idx))

    # Выбираем плагин в зависимости от транспорта
    local transport_plugin=""
    if [ "$transport" = "obfs4" ]; then
        transport_plugin="ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy"
    elif [ "$transport" = "webtunnel" ]; then
        # webtunnel поддерживается через obfs4proxy (начиная с версии 0.0.14)
        transport_plugin="ClientTransportPlugin webtunnel exec /usr/bin/obfs4proxy"
    fi

    cat > "$workdir/torrc" <<EOF
SocksPort $socks_port
ControlPort $control_port
DataDirectory $workdir/data
UseBridges 1
$transport_plugin
Bridge $bridge_line
Log notice file $workdir/tor.log
StrictNodes 1
EOF

    mkdir -p "$workdir/data"

    tor -f "$workdir/torrc" &>/dev/null &
    local tor_pid=$!

    local connected=0
    local elapsed=0

    while [ $elapsed -lt $timeout_sec ]; do
        if grep -q "Bootstrapped 100%" "$workdir/tor.log" 2>/dev/null; then
            connected=1
            break
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    kill "$tor_pid" 2>/dev/null || true
    wait "$tor_pid" 2>/dev/null || true
    rm -rf "$workdir"

    local ip_port
    ip_port=$(echo "$bridge_line" | awk '{print $2}')

    if [ $connected -eq 1 ]; then
        echo "$bridge_line" >> "$ok_file"
        echo -e "  ${GREEN}✅ [$transport] $ip_port${NC}"
    else
        echo -e "  ${RED}❌ [$transport] $ip_port${NC}"
    fi
}

export -f check_one
export GREEN RED NC

# ---------- запускаем параллельно ----------
START=$(date +%s)

i=0
pids=()

for bridge in "${BRIDGES[@]}"; do
    check_one "$bridge" "$i" "$TRANSPORT" "$OK_FILE" "$TOR_TIMEOUT" &
    pids+=($!)
    i=$((i + 1))

    if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
        wait "${pids[0]}"
        pids=("${pids[@]:1}")
    fi
done

for pid in "${pids[@]}"; do
    wait "$pid"
done

END=$(date +%s)
ELAPSED=$((END - START))

# ---------- итоги ----------
OK_COUNT=$(grep -c '' "$OK_FILE" 2>/dev/null || echo 0)
FAIL_COUNT=$((TOTAL - OK_COUNT))

echo ""
echo "══════════════════════════════════════════════════"
echo -e "${YELLOW}[$TRANSPORT]${NC}"
echo -e "${GREEN}✅ Рабочих:    $OK_COUNT / $TOTAL${NC}"
echo -e "${RED}❌ Нерабочих:  $FAIL_COUNT / $TOTAL${NC}"
echo -e "⏱️  Время:      ${ELAPSED}s"
echo -e "💾 Результат:  $OK_FILE"
echo "══════════════════════════════════════════════════"

