import re


IPV6_RE = re.compile(
    r'\[([^\]]+)\]:(\d+)'
)

IPV4_RE = re.compile(
    r'(?<!\S)(\d{1,3}(?:\.\d{1,3}){3}):(\d+)'
)


def extract_host_port(line: str):

    line = line.strip()

    # Убираем опциональный префикс "Bridge "
    if line.lower().startswith('bridge '):
        line = line[7:].strip()

    ipv6 = IPV6_RE.search(line)

    if ipv6:
        return ipv6.group(1), int(ipv6.group(2))

    ipv4 = IPV4_RE.search(line)

    if ipv4:
        return ipv4.group(1), int(ipv4.group(2))

    return None
