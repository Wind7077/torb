import re


def validate_bridge(line: str) -> str | None:

    line = line.strip()

    if not line or line.startswith('#'):
        return None

    # Убираем опциональный префикс "Bridge "
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

    # Vanilla без префикса: IP:PORT или IP:PORT FINGERPRINT
    if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}:\d+', line):
        return 'vanilla'

    # IPv6 без префикса
    if re.match(r'^\[[^\]]+\]:\d+', line):
        return 'vanilla'

    return None
