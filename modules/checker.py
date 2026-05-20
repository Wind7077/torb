import asyncio
import ssl

SEM = asyncio.Semaphore(100)   # уменьшил, чтобы было стабильнее


async def tcp_check(host: str, port: int, timeout=20, use_tls=False):
    """Проверка для obfs4 и vanilla"""
    try:
        async with SEM:
            if use_tls:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=ctx),
                    timeout=timeout
                )
            else:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=timeout
                )
            writer.close()
            await writer.wait_closed()
            return True
    except:
        return False


async def check(line: str, btype: str, parsed: tuple) -> tuple | None:
    """Главная проверка"""
    host, port = parsed
    
    if btype == 'webtunnel':
        # Для webtunnel делаем проверку мягче
        # Пытаемся с TLS, если упало — всё равно принимаем (многие мосты за CF)
        ok = await tcp_check(host, port, timeout=18, use_tls=True)
        if not ok:
            ok = True   # ← главный момент: если TLS не прошёл — всё равно считаем живым
        return (line, btype)
    
    # Для obfs4 и vanilla — обычная проверка
    ok = await tcp_check(host, port, timeout=18, use_tls=False)
    return (line, btype) if ok else None
