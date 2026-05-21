import asyncio
import aiohttp
import ssl
import re
import time

SEM_WEBTUNNEL = asyncio.Semaphore(50)

URL_RE = re.compile(r'url=([^\s]+)')
VER_RE = re.compile(r'ver=(\d+)\.(\d+)\.(\d+)')
FP_RE = re.compile(r'\b([A-F0-9]{40})\b', re.I)


def version_score(line: str) -> int:

    m = VER_RE.search(line)

    if not m:
        return -10

    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3))

    if (major, minor, patch) < (0, 0, 1):
        return -50

    if patch >= 4:
        return 20

    if patch >= 3:
        return 10

    return 0


def validate_webtunnel_line(line: str) -> bool:

    if not URL_RE.search(line):
        return False

    if not FP_RE.search(line):
        return False

    m = VER_RE.search(line)

    if not m:
        return False

    version = tuple(map(int, m.groups()))

    if version < (0, 0, 1):
        return False

    return True


async def _probe_webtunnel(
    url: str,
    timeout: int = 15
) -> int | None:

    try:

        async with SEM_WEBTUNNEL:

            ctx = ssl.create_default_context()

            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Upgrade': 'websocket',
                'Connection': 'Upgrade',
            }

            connector = aiohttp.TCPConnector(
                ssl=ctx,
                force_close=True,
            )

            start = time.perf_counter()

            async with aiohttp.ClientSession(
                connector=connector,
                headers=headers
            ) as s:

                async with s.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True
                ) as resp:

                    if resp.status >= 400:
                        return None

                    return round(
                        (time.perf_counter() - start) * 1000
                    )

    except:
        return None


async def reliable_webtunnel_check(
    line: str,
    retries: int = 2,
    delay: float = 2.0
) -> int | None:

    if not validate_webtunnel_line(line):
        return None

    m = URL_RE.search(line)

    if not m:
        return None

    url = m.group(1)

    results = []

    for _ in range(retries):

        ms = await _probe_webtunnel(url)

        if ms is None:
            return None

        results.append(ms)

        await asyncio.sleep(delay)

    return round(sum(results) / len(results))
