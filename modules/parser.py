import re

def extract_host_port(line: str):
    m = re.search(r'([^\s:]+):(\d+)', line)

    if not m:
        return None

    return m.group(1), int(m.group(2))

