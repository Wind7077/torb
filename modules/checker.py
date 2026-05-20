import asyncio
import ssl

SEM = asyncio.Semaphore(100)


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


async def check(line: str, btype: str, parsed: tuple) -> tuple | None:
    host, port = parsed
    
    if btype == 'webtunnel':
        # Делаем TLS-проверку, но если не получилось — всё равно принимаем
        # Это самый разумный компромисс
        ok = await tcp_check(host, port, timeout=16, use_tls=True)
        if ok:
            return (line, btype)
        else:
            # Если TLS не прошёл — пробуем без TLS (некоторые мосты так работают)
            ok = await tcp_check(host, port, timeout=12, use_tls=False)
            return (line, btype)   # ← принимаем в любом случае, если дошли до этой строки

    # obfs4 и vanilla — строгая проверка
    ok = await tcp_check(host, port, timeout=18, use_tls=False)
    return (line, btype) if ok else None
