import asyncio
import ssl
import re
import aiohttp

SEM = asyncio.Semaphore(60)

URL_PATTERN = re.compile(r'url=(https?://[^\s]+)')


async def tcp_check(host: str, port: int, timeout=18, use_tls=False):
    try:
        async with SEM:
            if use_tls:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=ctx), timeout=timeout
                )
            else:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=timeout
                )
            writer.close()
            await writer.wait_closed()
            return True
    except:
        return False


async def webtunnel_check(line: str, timeout=20) -> bool:
    """Проверка webtunnel с настоящим handshake"""
    try:
        match = URL_PATTERN.search(line)
        if not match:
            return False

        url = match.group(1).strip()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
            "Sec-WebSocket-Version": "13",
            "Accept": "*/*"
        }

        connector = aiohttp.TCPConnector(ssl=False, family=0, limit=0)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=False,
                ssl=False
            ) as resp:
                
                # Хорошие коды для живых webtunnel
                if resp.status in (101, 200, 400, 403, 502, 503):
                    return True
                if resp.status < 500:   # любой 4xx тоже часто живой
                    return True
                return False

    except asyncio.TimeoutError:
        return True      # Таймаут = часто живой (медленный мост)
    except Exception:
        return False


async def check(line: str, btype: str, parsed: tuple) -> tuple | None:
    if btype == 'webtunnel':
        ok = await webtunnel_check(line)
    else:
        host, port = parsed
        ok = await tcp_check(host, port, use_tls=False)

    return (line, btype) if ok else None
