FROM python:3.11-slim

# WeasyPrint's native stack (Pango/Cairo/GDK-Pixbuf) + fonts for the PDF report.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Self-contained by default: bundled SQLite snapshot, no external DB needed (e.g. Railway).
# docker-compose overrides DATABASE_URL to Postgres and PORT to 8000 for local dev.
ENV DATABASE_URL=sqlite:///data/race_data.db

# Bind the platform-injected PORT (Railway/Render); falls back to 7860, and compose sets 8000.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
