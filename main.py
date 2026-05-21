import asyncio
import aiohttp
import re
import ssl
import time
from collections import defaultdict
from pathlib import Path

from modules.validator import validate_bridge, normalize
from modules.parser import extract_host_port

OUTPUT_DIR = Path('bridges')
TOP_N = 15
SEM = asyncio.Semaphore(200)


# ── Fetch ────────────────────────────────────────────────────────────────────

async def fetch(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                print(f'[BAD] {url} -> {r.status}')
                return ''
            print(f'[OK] {url}')
            return await r.text()
    except Exception as e:
        print(f'[ERR] {url} -> {e}')
        return ''


# ── Latency / TCP check ───────────────────────────────────────────────────────

async def tcp_latency(host, port, timeout=8, use_tls=False):
    try:
        async with SEM:
            start = time.perf_counter()
            if use_tls:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=ctx), timeout=timeout)
            else:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=timeout)
            ms = round((time.perf_counter() - start) * 1000)
            writer.close()
            return ms
    except:
        return None  # None = мёртвый


async def webtunnel_latency(line, timeout=10):
    m = re.search(r'url=(https://[^ ]+)', line)
    if not m:
        return None
    url = m.group(1)
    try:
        async with SEM:
            start = time.perf_counter()
            ctx = ssl.create_default_context()
            conn = aiohttp.TCPConnector(ssl=ctx)
            async with aiohttp.ClientSession(connector=conn) as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                                 allow_redirects=True) as resp:
                    if resp.status >= 500:
                        return None
                    return round((time.perf_counter() - start) * 1000)
    except:
        return None


# ── Scoring ───────────────────────────────────────────────────────────────────

def port_score(port: int) -> int:
    if port == 443:   return 30
    if port == 8443:  return 20
    if port == 80:    return 15
    if port == 8080:  return 10
    if port > 50000:  return -20
    return 0


def latency_score(ms: int) -> int:
    if ms < 100:  return 40
    if ms < 300:  return 25
    if ms < 600:  return 10
    if ms < 1000: return 0
    return -10


# ── Cluster filter (/24) ──────────────────────────────────────────────────────

def slash24(ip: str) -> str:
    parts = ip.split('.')
    return '.'.join(parts[:3])


def dedupe_and_cluster(bridges: list) -> list:
    """
    - Дедупликация по IP+PORT+FINGERPRINT (первые 8 hex).
    - Из каждого /24 оставляем не более 2 мостов.
    """
    seen_key = set()
    cluster_count = defaultdict(int)
    result = []

    for b in bridges:
        hp = extract_host_port(b['line'])
        if not hp:
            continue
        host, port = hp

        # fingerprint — первые 8 символов (если есть)
        parts = b['line'].split()
        fp = next((p for p in parts if re.match(r'^[0-9A-F]{40}$', p, re.I)), '')[:8]
        key = f'{host}:{port}:{fp}'

        if key in seen_key:
            continue
        seen_key.add(key)

        # cluster /24 только для IPv4
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            net = slash24(host)
            if cluster_count[net] >= 2:
                continue
            cluster_count[net] += 1

        result.append(b)

    return result


# ── Process one bridge ────────────────────────────────────────────────────────

async def process_bridge(raw_line: str):
    line = normalize(raw_line)
    if not line or line.startswith('#'):
        return None

    # normalize Bridge prefix for validate
    check_line = line
    if check_line.lower().startswith('bridge '):
        check_line = check_line[7:].strip()

    transport = validate_bridge(line)
    if not transport:
        return None

    hp = extract_host_port(line)

    if transport == 'webtunnel':
        ms = await webtunnel_latency(line)
    elif hp:
        host, port = hp
        ms = await tcp_latency(host, port)
    else:
        ms = None

    if ms is None:
        return None  # мёртвый — выбрасываем

    score = latency_score(ms)
    if hp:
        _, port = hp
        score += port_score(port)

    return {
        'line': check_line,  # без Bridge-префикса
        'transport': transport,
        'latency': ms,
        'score': score,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

    results = await asyncio.gather(*[process_bridge(l) for l in raw])
    alive = [r for r in results if r]
    print(f'[INFO] живых мостов: {len(alive)}')

    # Кластеризация и дедупликация
    alive = dedupe_and_cluster(
        sorted(alive, key=lambda x: -x['score'])
    )
    print(f'[INFO] после кластеризации: {len(alive)}')

    # Сортировка: score desc, latency asc
    alive.sort(key=lambda x: (-x['score'], x['latency']))

    # Вывод статистики
    by_type = defaultdict(list)
    for b in alive:
        by_type[b['transport']].append(b)
    for t, lst in by_type.items():
        print(f'[INFO] {t}: {len(lst)}')

    # Топ-15 mixed (лучшие по score, по 1 от каждого типа по кругу если можно)
    mixed = []
    buckets = {t: list(v) for t, v in by_type.items()}
    types = [t for t in ['obfs4', 'webtunnel', 'vanilla', 'snowflake'] if t in buckets]
    i = 0
    while len(mixed) < TOP_N and any(buckets.get(t) for t in types):
        t = types[i % len(types)]
        if buckets.get(t):
            mixed.append(buckets[t].pop(0))
        i += 1

    # Файлы
    def save(name, bridges):
        path = OUTPUT_DIR / name
        lines = [b['line'] for b in bridges]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'[SAVED] {path} ({len(lines)})')

    save('mixed.txt', mixed)
    save('obfs4.txt', by_type.get('obfs4', [])[:TOP_N])
    save('webtunnel.txt', by_type.get('webtunnel', [])[:TOP_N])
    save('vanilla.txt', by_type.get('vanilla', [])[:TOP_N])
    save('snowflake.txt', by_type.get('snowflake', [])[:TOP_N])

    print(f'[DONE] mixed.txt: {len(mixed)} мостов')


if __name__ == '__main__':
    asyncio.run(main())
