FROM python:3.11.13-alpine3.22

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY entrypoint.py ./

ENTRYPOINT ["python", "entrypoint.py"]