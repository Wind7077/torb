import asyncio
import time

async def measure_latency(host: str, port: int, timeout=5):
    try:
        start = time.perf_counter()

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )

        latency = round((time.perf_counter() - start) * 1000)

        writer.close()
        await writer.wait_closed()

        return latency

    except:
        return 99999

