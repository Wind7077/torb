import asyncio
import aiohttp
import aiofiles

from modules.parser import extract_host_port
from modules.validator import validate_bridge
from modules.checker import tcp_check
from modules.latency import measure_latency


SOURCES_GITHUB = "sources/github.txt"
OUTPUT_DIR = "bridges"

BRIDGE_TYPES = ["obfs4", "webtunnel", "vanilla", "snowflake"]


async def fetch_url(session: aiohttp.ClientSession, url: str) -> list[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                text = await resp.text()
                return text.splitlines()
    except Exception as e:
        print(f"[!] Ошибка загрузки {url}: {e}")
    return []


async def process_bridges(lines: list[str]) -> dict[str, list[str]]:
    result = {t: [] for t in BRIDGE_TYPES}
    seen = set()

    tasks = []
    valid_lines = []

    for line in lines:
        line = line.strip()
        if not line or line in seen:
            continue
        bridge_type = validate_bridge(line)
        if bridge_type is None:
            continue
        parsed = extract_host_port(line)
        if parsed is None:
            continue
        seen.add(line)
        valid_lines.append((line, bridge_type, parsed))

    async def check(line, bridge_type, parsed):
        host, port = parsed
        ok = await tcp_check(host, port)
        if ok:
            lat = await measure_latency(host, port)
            return line, bridge_type, lat
        return None

    tasks = [check(l, bt, p) for l, bt, p in valid_lines]
    results = await asyncio.gather(*tasks)

    for r in results:
        if r is not None:
            line, bridge_type, lat = r
            result[bridge_type].append((lat, line))

    # Сортируем по латентности
    for t in BRIDGE_TYPES:
        result[t] = [line for _, line in sorted(result[t], key=lambda x: x[0])]

    return result


async def save_bridges(bridges: dict[str, list[str]]):
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for bridge_type, lines in bridges.items():
        if not lines:
            print(f"[~] {bridge_type}: нет рабочих мостов")
            continue
        path = os.path.join(OUTPUT_DIR, f"{bridge_type}.txt")
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write("\n".join(lines) + "\n")
        print(f"[+] {bridge_type}: {len(lines)} мостов → {path}")


async def main():
    # Загружаем список URL-источников
    async with aiofiles.open(SOURCES_GITHUB, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in await f.readlines() if line.strip()]

    all_lines = []
    async with aiohttp.ClientSession() as session:
        fetch_tasks = [fetch_url(session, url) for url in urls]
        fetched = await asyncio.gather(*fetch_tasks)
        for lines in fetched:
            all_lines.extend(lines)

    print(f"[*] Всего строк из источников: {len(all_lines)}")

    bridges = await process_bridges(all_lines)
    await save_bridges(bridges)


if __name__ == "__main__":
    asyncio.run(main())
