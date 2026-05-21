import asyncio
import aiohttp
import ssl
import re
import time

SEM_WEBTUNNEL = asyncio.Semaphore(50)

URL_RE = re.compile(r'url=(https://[^ ]+)')
VER_RE = re.compile(r'ver=(\d+)\.(\d+)\.(\d+)')


def get_version(line: str) -> tuple:
    m = VER_RE.search(line)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def version_score(line: str) -> int:
    major, minor, patch = get_version(line)
    if patch >= 3:
        return 15
    return -10


def is_version_ok(line: str) -> bool:
    """Пропускаем только ver=0.0.3 и выше."""
    _, _, patch = get_version(line)
    return patch >= 3


async def _head_once(url: str, timeout: int = 10) -> int | None:
    try:
        async with SEM_WEBTUNNEL:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn = aiohttp.TCPConnector(ssl=ctx)
            start = time.perf_counter()
            async with aiohttp.ClientSession(connector=conn) as s:
                async with s.head(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True
                ) as resp:
                    if resp.status >= 500:
                        return None
                    return round((time.perf_counter() - start) * 1000)
    except:
        return None


async def reliable_webtunnel_check(
    line: str,
    retries: int = 2,
    delay: float = 3.0
) -> int | None:
    # Отсекаем старые версии сразу — не тратим время на проверку
    if not is_version_ok(line):
        return None

    m = URL_RE.search(line)
    if not m:
        return None
    url = m.group(1)

    results = []
    for _ in range(retries):
        ms = await _head_once(url)
        if ms is None:
            return None
        results.append(ms)
        await asyncio.sleep(delay)
    return round(sum(results) / len(results))
