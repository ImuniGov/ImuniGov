FROM python:3.12-alpine

WORKDIR /app

COPY server.py app.js index.html patient.js patient.html home.html styles.css roles.css ./
COPY docs ./docs

ENV IMUNIGUI_HOST=0.0.0.0 \
    IMUNIGUI_PORT=4173 \
    IMUNIGUI_DATA_DIR=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 4173

CMD ["python", "server.py"]
