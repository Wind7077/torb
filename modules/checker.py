import asyncio
import ssl
import re
import aiohttp

# Ограничиваем параллельность, чтобы не убивать сеть и не получать бан
SEM = asyncio.Semaphore(80)

# Регулярка для извлечения url= из webtunnel строки
URL_PATTERN = re.compile(r'url=(https?://[^\s]+)')


async def tcp_check(host: str, port: int, timeout=18, use_tls=False):
    """Простая TCP-проверка для obfs4 / vanilla"""
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


async def webtunnel_check(line: str, timeout=25) -> bool:
    """Улучшенная проверка WebTunnel (имитирует реальное подключение)"""
    try:
        match = URL_PATTERN.search(line)
        if not match:
            return False
        
        url = match.group(1).strip()
        # Добавляем заголовки, которые ожидает webtunnel
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",  # dummy
            "Sec-WebSocket-Version": "13"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=timeout),
                ssl=False,          # сертификаты часто self-signed или Cloudflare
                allow_redirects=False
            ) as resp:
                # WebTunnel обычно отвечает 101 Switching Protocols или 502/403 при "правильном" запросе
                if resp.status in (101, 200, 502, 403):
                    return True
                # Иногда просто открытый TLS-порт — тоже считаем живым
                if resp.status == 400 or resp.status < 500:
                    return True
                return False

    except asyncio.TimeoutError:
        return False  # таймаут = возможно живой, но медленный
    except Exception:
        # Если вообще не соединился — мёртвый
        return False


async def check(line: str, btype: str, parsed: tuple) -> tuple | None:
    """Главная функция проверки"""
    host, port = parsed
    
    if btype == 'webtunnel':
        ok = await webtunnel_check(line)
    else:
        # Для obfs4/vanilla используем старую проверку
        ok = await tcp_check(host, port, use_tls=False)
    
    return (line, btype) if ok else None
