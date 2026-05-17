# 🧅 Tor Bridge Checker

Автоматически проверяет **obfs4** и **webtunnel** bridges через настоящий **tor + obfs4proxy**.  
Каждые **4 часа** GitHub Actions запускает проверку и обновляет два файла в корне репо.

## Результаты

| Файл | Содержимое |
|------|-----------|
| [`working_obfs4.txt`](./working_obfs4.txt) | Рабочие obfs4 bridges |
| [`working_webtunnel.txt`](./working_webtunnel.txt) | Рабочие webtunnel bridges |

## Как работает

```
GitHub Actions (Ubuntu, каждые 4 часа)
  ├── apt install tor obfs4proxy
  ├── скачивает TOR_BRIDGES_OBFS4.txt      → проверяет → working_obfs4.txt
  └── скачивает TOR_BRIDGES_WEBTUNNEL.txt  → проверяет → working_webtunnel.txt

Для каждого bridge:
  └── запускает отдельный tor с уникальным torrc
      └── ждёт "Bootstrapped 100%" в логе (до 25 сек)
          ├── успех   → записывает в working_*.txt
          └── таймаут → пропускает
  └── коммитит оба файла обратно в репо
```

## Источники

- [TOR_BRIDGES_OBFS4.txt](https://github.com/igareck/vpn-configs-for-russia/blob/main/TOR-BRIDGES/TOR_BRIDGES_OBFS4.txt)
- [TOR_BRIDGES_WEBTUNNEL.txt](https://github.com/igareck/vpn-configs-for-russia/blob/main/TOR-BRIDGES/TOR_BRIDGES_WEBTUNNEL.txt)

## Запустить вручную

**Actions → Tor Bridge Checker → Run workflow**

Или локально:

```bash
sudo apt install tor obfs4proxy
bash scripts/check_bridges.sh raw_obfs4.txt     obfs4     working_obfs4.txt
bash scripts/check_bridges.sh raw_webtunnel.txt webtunnel working_webtunnel.txt
```

## Структура репо

```
.
├── .github/workflows/check_bridges.yml
├── scripts/check_bridges.sh
├── working_obfs4.txt       ← обновляется каждые 4ч
├── working_webtunnel.txt   ← обновляется каждые 4ч
└── README.md
```

> ⚙️ **Settings → Actions → General → Workflow permissions → Read and write permissions**
