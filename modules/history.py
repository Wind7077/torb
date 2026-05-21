import json
from datetime import date
from pathlib import Path

HISTORY_FILE = Path('bridges_history.json')


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except:
            return {}
    return {}


def save_history(history: dict):
    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )


def update_entry(history: dict, fp: str, latency: int) -> dict:
    today = str(date.today())
    if fp not in history:
        history[fp] = {'seen': 0, 'avg_latency': latency, 'last_seen': today}
    entry = history[fp]
    entry['seen'] += 1
    entry['avg_latency'] = round(
        entry['avg_latency'] * 0.7 + latency * 0.3
    )
    entry['last_seen'] = today
    return history


def history_score(history: dict, fp: str, transport: str = 'obfs4') -> int:
    if fp not in history:
        return -10  # новый — не доверяем

    entry = history[fp]
    seen = entry['seen']
    avg_lat = entry['avg_latency']

    # порог медлительности зависит от типа:
    # webtunnel физически медленнее из-за HTTP+TLS overhead
    slow_threshold = 1200 if transport == 'webtunnel' else 600

    # хронически медленный (3+ проверок) — штраф
    if seen >= 3 and avg_lat > slow_threshold:
        return -20

    if seen >= 10: return 30
    if seen >= 5:  return 20
    if seen >= 3:  return 10
    if seen >= 1:  return 0
    return -10
