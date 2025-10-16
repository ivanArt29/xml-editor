FROM python:3.11-slim

# Системные зависимости для PyQt5
RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 libxrender1 libxext6 libxi6 libxrandr2 libxcursor1 libxinerama1 \
    libglib2.0-0 libsm6 libxkbcommon-x11-0 libxkbcommon0 \
    libxcb1 libxcb-xinerama0 libxcb-render0 libxcb-shape0 libxcb-shm0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xfixes0 \
    libqt5gui5 libqt5widgets5 libqt5printsupport5 qtbase5-dev \
    fonts-dejavu-core \
    xvfb xauth x11vnc fluxbox novnc websockify \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ускоряем установку зависимостей
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Значение по умолчанию 
ENV QT_QPA_PLATFORM=xcb


COPY start_vnc.sh /app/start_vnc.sh
RUN chmod +x /app/start_vnc.sh

CMD ["bash", "-lc", "xvfb-run -a pytest -q"]


