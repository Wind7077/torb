import asyncio
import aiohttp
from pathlib import Path

from modules.validator import validate_bridge
from modules.parser import extract_host_port
from modules.checker import tcp_check
from modules.latency import measure_latency


OUTPUT_DIR = Path('output')


async def fetch(session, url):

    try:

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=20)
        ) as response:

            if response.status != 200:
                print(f'[BAD STATUS] {url} -> {response.status}')
                return ''

            print(f'[OK] {url}')

            return await response.text()

    except Exception as e:

        print(f'[FETCH ERROR] {url} -> {e}')

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


async def save_file(name, lines):

    path = OUTPUT_DIR / name

    with open(path, 'w', encoding='utf-8') as f:

        f.write(
            '\n'.join(lines)
        )

    print(f'[SAVED] {path} ({len(lines)} lines)')


async def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    github_sources = open(
        'sources/github.txt',
        encoding='utf-8'
    ).read().splitlines()

    github_sources = [
        x.strip()
        for x in github_sources
        if x.strip()
    ]

    print(f'[INFO] loaded {len(github_sources)} sources')

    all_lines = set()

    async with aiohttp.ClientSession() as session:

        tasks = [
            fetch(session, url)
            for url in github_sources
        ]

        pages = await asyncio.gather(*tasks)

    for page in pages:

        for line in page.splitlines():

            line = line.strip()

            if line:
                all_lines.add(line)

    print(f'[INFO] loaded {len(all_lines)} raw lines')

    valid_lines = []

    for line in all_lines:

        if validate_bridge(line):

            valid_lines.append(line)

    print(f'[INFO] validated {len(valid_lines)} bridges')

    tasks = [
        process_bridge(line)
        for line in valid_lines
    ]

    results = await asyncio.gather(*tasks)

    bridges = [
        r for r in results
        if r
    ]

    print(f'[INFO] alive {len(bridges)} bridges')

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

    await save_file(
        'mixed.txt',
        mixed
    )

    await save_file(
        'obfs4.txt',
        obfs4
    )

    await save_file(
        'webtunnel.txt',
        webtunnel
    )

    await save_file(
        'vanilla.txt',
        vanilla
    )

    await save_file(
        'snowflake.txt',
        snowflake
    )

    print(
        f'[DONE] saved {len(bridges)} bridges'
    )


if __name__ == '__main__':

    asyncio.run(main())
