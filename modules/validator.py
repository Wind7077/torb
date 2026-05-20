import re


def validate_bridge(line: str) -> str | None:

    line = line.strip()

    if not line or line.startswith('#'):
        return None

    # Убираем опциональный префикс "Bridge " (torrc-формат)
    if line.lower().startswith('bridge '):
        line = line[7:].strip()

    if line.startswith('obfs4 '):
        return 'obfs4'

    if line.startswith('webtunnel '):
        return 'webtunnel'

    if line.startswith('vanilla '):
        return 'vanilla'

    if line.startswith('snowflake '):
        return 'snowflake'

    # Vanilla-мосты без префикса: просто IP:PORT или [IPv6]:PORT
    bare_ipv4 = re.match(r'^\d{1,3}(?:\.\d{1,3}){3}:\d+$', line)
    if bare_ipv4:
        return 'vanilla'

    bare_ipv6 = re.match(r'^\[[^\]]+\]:\d+$', line)
    if bare_ipv6:
        return 'vanilla'

    return None
