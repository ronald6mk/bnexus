FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data samples

# Render/Railway set PORT
ENV PORT=8787
EXPOSE 8787

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
