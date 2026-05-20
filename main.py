import asyncio
import aiohttp
import aiofiles
import os
import re

from modules.parser import extract_host_port
from modules.validator import validate_bridge
from modules.checker import tcp_check


SOURCES_FILE = "sources/github.txt"
OUTPUT_DIR = "bridges"
BRIDGE_TYPES = ["obfs4", "webtunnel", "vanilla", "snowflake"]


async def fetch_url(session: aiohttp.ClientSession, url: str) -> list[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            print(f"[HTTP {resp.status}] {url}")
            if resp.status == 200:
                text = await resp.text()
                lines = [l for l in text.splitlines() if l.strip()]
                print(f"  → {len(lines)} непустых строк")
                return lines
            else:
                print(f"  → ПРОПУЩЕНО (не 200)")
    except Exception as e:
        print(f"  → ОШИБКА: {e}")
    return []


async def main():
    async with aiofiles.open(SOURCES_FILE, "r") as f:
        urls = [l.strip() for l in await f.readlines() if l.strip()]

    print(f"[*] Источников: {len(urls)}")

    all_lines = []
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch_url(session, u) for u in urls])
        for lines in results:
            all_lines.extend(lines)

    print(f"\n[*] Всего строк: {len(all_lines)}")

    # Считаем сколько строк каждого типа до проверки
    type_counts = {t: 0 for t in BRIDGE_TYPES}
    type_counts["unknown"] = 0
    valid = []

    for line in all_lines:
        btype = validate_bridge(line)
        if btype:
            type_counts[btype] += 1
            parsed = extract_host_port(line)
            if parsed:
                valid.append((line, btype, parsed))
        else:
            type_counts["unknown"] += 1

    print("\n[*] После валидации:")
    for t, c in type_counts.items():
        print(f"  {t}: {c}")
    print(f"  с распознанным host:port: {len(valid)}")

    # Показываем примеры "unknown" строк — это самое важное для диагностики
    unknown_examples = []
    for line in all_lines:
        if validate_bridge(line) is None and len(unknown_examples) < 10:
            unknown_examples.append(line)
    if unknown_examples:
        print("\n[!] Примеры непризнанных строк:")
        for l in unknown_examples:
            print(f"  {repr(l[:120])}")

    # TCP-проверка
    print(f"\n[*] TCP-проверка {len(valid)} мостов...")

    async def check(line, btype, parsed):
        host, port = parsed
        ok = await tcp_check(host, port)
        return (line, btype) if ok else None

    tasks = [check(l, bt, p) for l, bt, p in valid]
    checked = await asyncio.gather(*tasks)
    alive = [r for r in checked if r]

    alive_counts = {t: 0 for t in BRIDGE_TYPES}
    for _, btype in alive:
        alive_counts[btype] += 1

    print("[*] Живых мостов после TCP:")
    for t, c in alive_counts.items():
        print(f"  {t}: {c}")

    # Запись файлов
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    buckets = {t: [] for t in BRIDGE_TYPES}
    for line, btype in alive:
        buckets[btype].append(line)

    for btype, lines in buckets.items():
        if not lines:
            print(f"[~] {btype}: нет живых — файл не создан")
            continue
        path = os.path.join(OUTPUT_DIR, f"{btype}.txt")
        async with aiofiles.open(path, "w") as f:
            await f.write("\n".join(lines) + "\n")
        print(f"[+] {path}: {len(lines)} мостов записано")


if __name__ == "__main__":
    asyncio.run(main())
