FROM python:3.12-alpine

# docker-cli: bootstrap.py creates the data directories in, and restarts, the
# XNAT container through the mounted docker socket.
RUN apk add --no-cache docker-cli

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bootstrap.py populate.py wait_for_api.py ./

CMD ["python", "bootstrap.py"]
