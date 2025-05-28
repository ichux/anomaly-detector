FROM python:3.12.10-slim-bookworm AS slim-bookworm

COPY requirements.txt ./

RUN pip3 install -U pip setuptools wheel && pip3 install -r requirements.txt && \
    find /usr/local/lib/python* -name '__pycache__' -type d -print0 | xargs -0 /bin/rm -rf '{}' && \
    find /usr/local/lib/python* -iname '*.pyc' -delete

FROM python:3.12.10-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=slim-bookworm /usr/local/bin /usr/local/bin
COPY --from=slim-bookworm /usr/local/lib/python3.12 /usr/local/lib/python3.12

WORKDIR /app
