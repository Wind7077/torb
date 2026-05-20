import aiohttp
import ssl
import re


URL_RE = re.compile(
    r'url=(https://[^ ]+)'
)


async def check_webtunnel(
    line,
    timeout=10
):

    try:

        m = URL_RE.search(line)

        if not m:
            return False

        url = m.group(1)

        ssl_context = ssl.create_default_context()

        connector = aiohttp.TCPConnector(
            ssl=ssl_context
        )

        async with aiohttp.ClientSession(
            connector=connector
        ) as session:

            async with session.get(
                url,
                timeout=timeout,
                allow_redirects=True
            ) as response:

                return response.status < 500

    except:

        return False
