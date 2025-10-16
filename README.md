# XML Editor (PyQt5)

Офлайн‑редактор XML на PyQt5 с деревом элементов, подсветкой синтаксиса, поиском/заменой и экспортом в HTML/PDF.

## Возможности
- Открытие/сохранение XML; дерево с ленивой подгрузкой
- Подсветка синтаксиса XML
- Поиск/замена (plain text; «Регистр», «Целое слово»)
- Экспорт: HTML, PDF; печать

## Требования
- Python 3.11+
- Windows/Linux/macOS
- PyQt 5

## Установка (локально)
```bash
pip install -r requirements.txt
python main.py
```

## Запуск через Docker
В проекте есть Dockerfile и docker-compose.yml. 

Запуск noVNC/VNC внутри контейнера
```bash
docker compose up --build app-vnc
```
- Браузер: `http://localhost:6080` (noVNC)
- VNC‑клиент: `localhost:5900`

## Тесты
Локально:
```bash
pytest -q
```
В Docker:
```bash
docker compose up --build tests
```

## Структура
- `main.py` — главное окно
- `tree_builder.py` — построение дерева (потоки)
- `syntax_highlighter.py` — подсветка XML
- `file_loader.py` — загрузка файлов
- `exporter.py` — экспорт HTML/PDF
- `start_vnc.sh` — Xvfb + VNC/noVNC
