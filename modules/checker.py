import asyncio
import ssl

SEM = asyncio.Semaphore(300)


async def tcp_check(host: str, port: int, timeout=15, use_tls=False):

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

            return True

    except:
        return False
