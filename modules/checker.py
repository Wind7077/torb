import asyncio

SEM = asyncio.Semaphore(300)


async def tcp_check(host: str, port: int, timeout=15):

    try:

        async with SEM:

            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )

            writer.close()

            return True

    except:
        return False
