import asyncio
import ssl
import os
import time

SEM = asyncio.Semaphore(200)
SEM_WEBTUNNEL = asyncio.Semaphore(50)


async def deep_tcp_check(host: str, port: int, timeout: int = 8) -> int | None:
    """
    Открывает TCP, шлёт случайные байты, ждёт 1 сек.
    Если RST не пришёл — мост живой. Возвращает латентность в мс или None.
    """
    try:
        async with SEM:
            start = time.perf_counter()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            ms = round((time.perf_counter() - start) * 1000)
            writer.write(os.urandom(16))
            await writer.drain()
            try:
                await asyncio.wait_for(reader.read(1), timeout=1.0)
            except asyncio.TimeoutError:
                pass  # таймаут = мост не сбросил соединение = живой
            writer.close()
            return ms
    except:
        return None


async def reliable_check(
    host: str,
    port: int,
    retries: int = 2,
    delay: float = 3.0
) -> int | None:
    """
    Проверяет мост retries раз с паузой delay сек.
    Возвращает среднюю латентность только если ВСЕ попытки успешны.
    """
    results = []
    for _ in range(retries):
        ms = await deep_tcp_check(host, port)
        if ms is None:
            return None  # хотя бы одна упала — выбрасываем
        results.append(ms)
        await asyncio.sleep(delay)
    return round(sum(results) / len(results))
