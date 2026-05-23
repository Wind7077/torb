import json
from datetime import date
from pathlib import Path

HISTORY_FILE = Path('bridges_history.json')

# Максимальный seen — дальше не считаем, убираем перекос старых мостов
MAX_SEEN = 50


def load_history() -> dict:
    if HISTORY_FILE.exists():
        try:
            h = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
            # Убираем мусор трёх типов:
            # 1. seen<=2 и lat>400 — webtunnel до фикса версий
            # 2. seen>=3 и lat>1200 — безнадёжно медленные
            # 3. seen>=10 и lat>800 — стабильно присутствуют но хронически медленные
            cleaned = {fp: v for fp, v in h.items()
                       if not (v['seen'] <= 2 and v['avg_latency'] > 400)
                       and not (v['seen'] >= 3 and v['avg_latency'] > 1200)
                       and not (v['seen'] >= 10 and v['avg_latency'] > 800)}
            if len(cleaned) < len(h):
                print(f'[INFO] очищено из истории: {len(h) - len(cleaned)} мусорных записей')
            return cleaned
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
    # Капаем seen на MAX_SEEN — дальше не растёт
    entry['seen'] = min(entry['seen'] + 1, MAX_SEEN)
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
    last_seen = entry.get('last_seen', '2000-01-01')

    # порог медлительности зависит от типа
    slow_threshold = 1200 if transport == 'webtunnel' else 600

    # хронически медленный (3+ проверок) — штраф
    if seen >= 3 and avg_lat > slow_threshold:
        return -20

    # базовый score по seen
    if seen >= 10: score = 30
    elif seen >= 5: score = 20
    elif seen >= 3: score = 10
    elif seen >= 1: score = 0
    else:           score = -10

    # штраф за давно не виденные мосты
    try:
        days_ago = (date.today() - date.fromisoformat(last_seen)).days
        if days_ago > 14:
            score = max(score - 20, -10)
        elif days_ago > 7:
            score = max(score - 15, -10)
        elif days_ago > 3:
            score = max(score - 5, -10)
    except ValueError:
        pass

    return score
