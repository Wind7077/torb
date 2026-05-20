import asyncio
import aiohttp
from pathlib import Path

from modules.validator import validate_bridge
from modules.parser import extract_host_port
from modules.checker import tcp_check
from modules.latency import measure_latency


async def fetch(session, url):
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=20)
        ) as r:

            if r.status != 200:
                return ''

            return await r.text()

    except:
        return ''


async def process_bridge(line):
    line = line.strip()

    if not line:
        return None

    transport = validate_bridge(line)

    if not transport:
        return None

    hp = extract_host_port(line)

    if not hp:
        return None

    host, port = hp

    alive = await tcp_check(host, port)

    if not alive:
        return None

    latency = await measure_latency(host, port)

    return {
        'line': line,
        'latency': latency,
        'transport': transport
    }


async def main():

    Path('output').mkdir(
        parents=True,
        exist_ok=True
    )

    github_sources = open(
        'sources/github.txt',
        encoding='utf-8'
    ).read().splitlines()

    all_lines = set()

    async with aiohttp.ClientSession() as session:

        tasks = [
            fetch(session, url)
            for url in github_sources
            if url.strip()
        ]

        pages = await asyncio.gather(*tasks)

    for page in pages:

        for line in page.splitlines():

            line = line.strip()

            if line:
                all_lines.add(line)

    tasks = [
        process_bridge(line)
        for line in all_lines
    ]

    results = await asyncio.gather(*tasks)

    bridges = [
        r for r in results
        if r
    ]

    bridges.sort(
        key=lambda x: x['latency']
    )

    mixed = []
    obfs4 = []
    webtunnel = []
    vanilla = []
    snowflake = []

    for bridge in bridges:

        line = bridge['line']
        transport = bridge['transport']

        mixed.append(line)

        if transport == 'obfs4':
            obfs4.append(line)

        elif transport == 'webtunnel':
            webtunnel.append(line)

        elif transport == 'vanilla':
            vanilla.append(line)

        elif transport == 'snowflake':
            snowflake.append(line)

    with open(
        'output/mixed.txt',
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(mixed)
        )

    with open(
        'output/obfs4.txt',
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(obfs4)
        )

    with open(
        'output/webtunnel.txt',
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(webtunnel)
        )

    with open(
        'output/vanilla.txt',
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(vanilla)
        )

    with open(
        'output/snowflake.txt',
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(snowflake)
        )

    print(
        f'saved {len(bridges)} bridges'
    )


if __name__ == '__main__':
    asyncio.run(main())
