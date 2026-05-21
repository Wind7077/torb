import asyncio
import aiohttp
import ssl
import re
import socket
from aiohttp import ClientSession

URL_RE = re.compile(r'url=([^\s]+)')
FPR_RE = re.compile(r'\b([A-F0-9]{40})\b')
VER_RE = re.compile(r'ver=([^\s]+)')


def is_valid_fingerprint(line: str) -> bool:
    m = FPR_RE.search(line)
    return bool(m)


def get_webtunnel_version(line: str):
    m = VER_RE.search(line)

    if not m:
        return None

    return m.group(1).strip()


def has_valid_url(line: str) -> bool:
    m = URL_RE.search(line)

    if not m:
        return False

    url = m.group(1)

    return url.startswith('https://')


def validate_bridge(line: str):

    line = line.strip()

    if not line:
        return None

    lower = line.lower()

    if lower.startswith('obfs4 '):
        return 'obfs4'

    if lower.startswith('vanilla '):
        return 'vanilla'

    if lower.startswith('webtunnel '):

        if not has_valid_url(line):
            return None

        if not is_valid_fingerprint(line):
            return None

        version = get_webtunnel_version(line)

        if version is None:
            return None

        # старые webtunnel часто мертвые
        if version == '0.0.1':
            return None

        return 'webtunnel'

    return None


async def validate_webtunnel_transport(url: str) -> bool:

    timeout = aiohttp.ClientTimeout(total=15)

    ssl_ctx = ssl.create_default_context()

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Upgrade': 'websocket',
        'Connection': 'Upgrade'
    }

    try:

        async with ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(
                url,
                ssl=ssl_ctx,
                allow_redirects=True
            ) as r:

                # endpoint мертв
                if r.status >= 400:
                    return False

                # нужен HTTP/2
                if r.version.major < 2:
                    return False

                return True

    except Exception:
        return False


async def validate_tcp(host: str, port: int) -> bool:

    try:

        fut = asyncio.open_connection(host, port)

        reader, writer = await asyncio.wait_for(fut, timeout=10)

        writer.close()

        await writer.wait_closed()

        return True

    except Exception:
        return False


async def check_bridge(line: str):

    bridge_type = validate_bridge(line)

    if not bridge_type:
        return None

    # webtunnel
    if bridge_type == 'webtunnel':

        m = URL_RE.search(line)

        if not m:
            return None

        url = m.group(1)

        ok = await validate_webtunnel_transport(url)

        if ok:
            return line

        return None

    # vanilla / obfs4
    try:

        parts = line.split()

        hostport = parts[1]

        if hostport.startswith('['):

            hp = hostport.split(']:')

            host = hp[0][1:]

            port = int(hp[1])

        else:

            host, port = hostport.split(':')

            port = int(port)

        ok = await validate_tcp(host, port)

        if ok:
            return line

        return None

    except Exception:
        return None


async def process_bridges(input_file, output_file):

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [x.strip() for x in f.readlines() if x.strip()]

    tasks = []

    for line in lines:
        tasks.append(check_bridge(line))

    results = await asyncio.gather(*tasks)

    working = [x for x in results if x]

    with open(output_file, 'w', encoding='utf-8') as f:

        for line in working:
            f.write(line + '\n')

    print(f'working bridges: {len(working)}')


if __name__ == '__main__':

    asyncio.run(
        process_bridges(
            'bridges.txt',
            'working_bridges.txt'
        )
    )
