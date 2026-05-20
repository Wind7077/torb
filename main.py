import asyncio
import aiohttp

from modules.validator import validate_bridge
from modules.parser import extract_host_port
from modules.checker import tcp_check
from modules.latency import measure_latency

async def fetch(session, url):
    try:
        async with session.get(url, timeout=20) as r:
            return await r.text()
    except:
        return ''

async def process_bridge(line):
    line = line.strip()

    if not validate_bridge(line):
        return None

    hp = extract_host_port(line)

    if not hp:
        return None

    host, port = hp

    alive = await tcp_check(host, port)

    if not alive:
        return None

    latency = await measure_latency(host, port)

    return (latency, line)

async def main():
    urls = open(
        'sources/github.txt',
        encoding='utf-8'
    ).read().splitlines()

    lines = set()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        pages = await asyncio.gather(*tasks)

    for page in pages:
        for line in page.splitlines():
            lines.add(line.strip())

    tasks = [process_bridge(line) for line in lines]

    results = await asyncio.gather(*tasks)

    valid = [r for r in results if r]

    valid.sort(key=lambda x: x[0])

    with open('output/mixed.txt', 'w', encoding='utf-8') as f:
        for _, line in valid:
            f.write(line + '\n')

    print(f'saved {len(valid)} bridges')

if __name__ == '__main__':
    asyncio.run(main())
