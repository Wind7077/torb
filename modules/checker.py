import asyncio

SEM = asyncio.Semaphore(300)


async def tcp_check(host: str, port: int, timeout=8):

    try:

        async with SEM:

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )

            writer.close()

            await writer.wait_closed()

            return True

    except:
        return False
