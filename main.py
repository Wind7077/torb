import asyncio
import aiohttp
import time

from pathlib import Path

from modules.validator import validate_bridge
from modules.parser import extract_host_port


OUTPUT_DIR = Path('output')

SEM = asyncio.Semaphore(300)


async def fetch(session, url):

    try:

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:

            if response.status != 200:

                print(
                    f'[BAD STATUS] {url} -> {response.status}'
                )

                return ''

            print(
                f'[OK] {url}'
            )

            return await response.text()

    except Exception as e:

        print(
            f'[FETCH ERROR] {url} -> {e}'
        )

        return ''


async def measure_latency(
    host,
    port,
    timeout=3
):

    try:

        async with SEM:

            start = time.perf_counter()

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host,
                    port
                ),
                timeout=timeout
            )

            latency = round(
                (time.perf_counter() - start) * 1000
            )

            writer.close()

            await writer.wait_closed()

            return latency

    except:

        return 99999


async def process_bridge(line):

    line = line.strip()

    if not line:
        return None

    transport = validate_bridge(line)

    if not transport:
        return None

    latency = 99999

    if transport != 'webtunnel':

        hp = extract_host_port(line)

        if hp:

            host, port = hp

            latency = await measure_latency(
                host,
                port
            )

    return {
        'line': line,
        'latency': latency,
        'transport': transport
    }


async def save_file(
    filename,
    lines
):

    path = OUTPUT_DIR / filename

    with open(
        path,
        'w',
        encoding='utf-8'
    ) as f:

        f.write(
            '\n'.join(lines)
        )

    print(
        f'[SAVED] {path} ({len(lines)} lines)'
    )


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

    print(
        f'[INFO] loaded {len(github_sources)} sources'
    )

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

            if not line:
                continue

            if line.startswith('#'):
                continue

            all_lines.add(line)

    print(
        f'[INFO] loaded {len(all_lines)} raw lines'
    )

    valid_lines = []

    for line in all_lines:

        transport = validate_bridge(line)

        if transport:

            valid_lines.append(
                (
                    line,
                    transport
                )
            )

    print(
        f'[INFO] validated {len(valid_lines)} bridges'
    )

    tasks = [
        process_bridge(line)
        for line, _ in valid_lines
    ]

    results = await asyncio.gather(*tasks)

    bridges = [
        r for r in results
        if r
    ]

    print(
        f'[INFO] processed {len(bridges)} bridges'
    )

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
