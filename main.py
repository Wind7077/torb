import asyncio
import aiohttp
import re
from collections import defaultdict
from pathlib import Path

from modules.validator import validate_bridge, normalize
from modules.parser import extract_host_port
from modules.checker import reliable_check
from modules.webtunnel_checker import reliable_webtunnel_check, version_score
from modules.history import load_history, save_history, update_entry, history_score
from modules.geoip import get_country, country_score, country_limit_ok

OUTPUT_DIR = Path('bridges')
TOP_N = 15
FP_RE = re.compile(r'\b([0-9A-F]{40})\b', re.I)


# ── Fetch ─────────────────────────────────────────────────────────────────────

async def fetch(session, url: str) -> str:
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as r:
            if r.status != 200:
                print(f'[BAD] {url} -> {r.status}')
                return ''
            print(f'[OK] {url}')
            return await r.text()
    except Exception as e:
        print(f'[ERR] {url} -> {e}')
        return ''


# ── Scoring helpers ───────────────────────────────────────────────────────────

def port_score(port: int) -> int:
    if port == 443:  return 30
    if port == 8443: return 20
    if port == 80:   return 15
    if port == 8080: return 10
    if port > 50000: return -20
    return 0


def latency_score(ms: int) -> int:
    if ms < 100:  return 40
    if ms < 300:  return 25
    if ms < 600:  return 10
    if ms < 1000: return 0
    return -10


def slash24(ip: str) -> str:
    return '.'.join(ip.split('.')[:3])


def extract_fp(line: str) -> str:
    m = FP_RE.search(line)
    return m.group(1).upper() if m else ''


# ── Process one bridge ────────────────────────────────────────────────────────

async def process_bridge(raw: str, history: dict) -> dict | None:
    line = normalize(raw)
    if not line or line.startswith('#'):
        return None

    # убираем Bridge-префикс для валидации
    clean = line[7:].strip() if line.lower().startswith('bridge ') else line
    transport = validate_bridge(clean)
    if not transport:
        return None

    hp = extract_host_port(clean)
    fp = extract_fp(clean)

    # ── Живость ──
    if transport == 'webtunnel':
        ms = await reliable_webtunnel_check(clean)
    elif hp:
        host, port = hp
        ms = await reliable_check(host, port)
    else:
        return None

    if ms is None:
        return None  # мёртвый

    # ── Score ──
    score = latency_score(ms)

    if hp:
        _, port = hp
        score += port_score(port)

    if transport == 'webtunnel':
        score += version_score(clean)

    # передаём transport чтобы порог медлительности был правильным
    score += history_score(history, fp, transport)

    country = 'XX'
    if hp:
        host, _ = hp
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            country = get_country(host)
            score += country_score(country)

    return {
        'line': clean,
        'transport': transport,
        'latency': ms,
        'score': score,
        'fp': fp,
        'country': country,
        'hp': hp,
    }


# ── Dedupe + cluster filter ───────────────────────────────────────────────────

def dedupe_and_filter(bridges: list) -> list:
    seen_fp = set()
    seen_ipport = set()
    cluster24 = defaultdict(int)
    country_count = defaultdict(int)

    result = []
    for b in bridges:
        fp = b['fp']
        hp = b['hp']

        # дедупликация по полному fingerprint
        if fp and fp in seen_fp:
            continue
        if fp:
            seen_fp.add(fp)

        # дедупликация по IP:PORT
        if hp:
            key = f'{hp[0]}:{hp[1]}'
            if key in seen_ipport:
                continue
            seen_ipport.add(key)

        # кластер /24 — максимум 2 из одной подсети
        if hp and re.match(r'^\d+\.\d+\.\d+\.\d+$', hp[0]):
            net = slash24(hp[0])
            if cluster24[net] >= 2:
                continue
            cluster24[net] += 1

        # страновой лимит — максимум 3 из одной страны
        c = b['country']
        if c != 'XX' and not country_limit_ok(country_count, c, limit=3):
            continue
        country_count[c] += 1

        result.append(b)

    return result


# ── Build mixed top-N with type rotation ──────────────────────────────────────

def build_mixed(by_type: dict, n: int) -> list:
    buckets = {t: list(v) for t, v in by_type.items()}
    order = [t for t in ['obfs4', 'obfs4', 'webtunnel', 'vanilla']
             if t in buckets]
    mixed = []
    i = 0
    while len(mixed) < n and any(buckets.get(t) for t in order):
        t = order[i % len(order)]
        if buckets.get(t):
            mixed.append(buckets[t].pop(0))
        i += 1
    return mixed


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    print(f'[INFO] история: {len(history)} записей')

    urls = [u.strip() for u in
            open('sources/github.txt', encoding='utf-8').readlines()
            if u.strip()]
    print(f'[INFO] источников: {len(urls)}')

    async with aiohttp.ClientSession() as session:
        pages = await asyncio.gather(*[fetch(session, u) for u in urls])

    raw = set()
    for page in pages:
        for line in page.splitlines():
            line = normalize(line)
            if line and not line.startswith('#'):
                raw.add(line)
    print(f'[INFO] уникальных строк: {len(raw)}')

    results = await asyncio.gather(*[process_bridge(l, history) for l in raw])
    alive = [r for r in results if r]
    print(f'[INFO] живых мостов (2x retry): {len(alive)}')

    # обновляем историю для живых
    for b in alive:
        if b['fp']:
            history = update_entry(history, b['fp'], b['latency'])
    save_history(history)
    print(f'[INFO] история сохранена: {len(history)} записей')

    # сортировка: score desc, latency asc
    alive.sort(key=lambda x: (-x['score'], x['latency']))

    # дедупликация и кластеризация
    alive = dedupe_and_filter(alive)
    print(f'[INFO] после фильтров: {len(alive)}')

    by_type = defaultdict(list)
    for b in alive:
        by_type[b['transport']].append(b)

    for t, lst in by_type.items():
        print(f'[INFO] {t}: {len(lst)} | лучший score={lst[0]["score"]} lat={lst[0]["latency"]}ms')

    def save(name, bridges):
        path = OUTPUT_DIR / name
        lines = [b['line'] for b in bridges]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'[SAVED] {path} ({len(lines)})')

    mixed = build_mixed(by_type, TOP_N)
    save('mixed.txt', mixed)
    save('obfs4.txt', by_type.get('obfs4', [])[:TOP_N])
    save('webtunnel.txt', by_type.get('webtunnel', [])[:TOP_N])
    save('vanilla.txt', by_type.get('vanilla', [])[:TOP_N])
    save('snowflake.txt', by_type.get('snowflake', [])[:TOP_N])

    print(f'[DONE] mixed.txt: {len(mixed)} мостов')


if __name__ == '__main__':
    asyncio.run(main())
