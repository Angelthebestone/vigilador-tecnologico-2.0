FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml SPEC_V2.md /app/
COPY src /app/src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "vigilancia_multiagente.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
