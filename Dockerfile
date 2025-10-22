FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ARG APP_DIR=/app
WORKDIR "$APP_DIR"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    poppler-utils \
    pkg-config \
    python3-dev \
    python3-pip \
    git && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libxrender1 libxext6 libsm6


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


ENV PYTHONPATH="$APP_DIR"
ENV CUDA_VISIBLE_DEVICES=0
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
