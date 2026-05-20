import re


IPV6_RE = re.compile(
    r'\[([^\]]+)\]:(\d+)'
)

IPV4_RE = re.compile(
    r'([^\s:]+):(\d+)'
)


def extract_host_port(line: str):

    line = line.strip()

    ipv6 = IPV6_RE.search(line)

    if ipv6:

        host = ipv6.group(1)

        port = int(
            ipv6.group(2)
        )

        return host, port

    ipv4 = IPV4_RE.search(line)

    if ipv4:

        host = ipv4.group(1)

        port = int(
            ipv4.group(2)
        )

        return host, port

    return None
