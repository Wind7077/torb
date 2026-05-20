import asyncio
import ssl
import re
import aiohttp

SEM = asyncio.Semaphore(60)  # уменьшили, чтобы меньше ложных отказов

URL_PATTERN = re.compile(r'url=(https?://[^\s]+)')


async def tcp_check(host: str, port: int, timeout=20, use_tls=False):
    """Обычная проверка для obfs4/vanilla"""
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


async def webtunnel_check(line: str, timeout=22) -> bool:
    """Улучшенная проверка WebTunnel (работает с IPv6 и Cloudflare)"""
    try:
        match = URL_PATTERN.search(line)
        if not match:
            return False

        url = match.group(1).strip()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        connector = aiohttp.TCPConnector(
            ssl=False,
            family=0,           # 0 = поддержка IPv4 + IPv6
            limit=0
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
                ssl=False
            ) as resp:
                # Многие живые webtunnel возвращают 403, 502, 400, 502 или 200
                if resp.status in (101, 200, 400, 403, 502, 503):
                    return True
                # Если вообще ответил — считаем живым
                return resp.status < 600

    except asyncio.TimeoutError:
        return True          # таймаут часто = живой мост (медленный)
    except Exception:
        return False         # только полная ошибка соединения = мёртвый


async def check(line: str, btype: str, parsed: tuple) -> tuple | None:
    """Главная проверка"""
    if btype == 'webtunnel':
        ok = await webtunnel_check(line)
    else:
        host, port = parsed
        ok = await tcp_check(host, port, use_tls=False)

    return (line, btype) if ok else None
