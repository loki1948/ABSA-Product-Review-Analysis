# Backend image: FastAPI + the ABSA pipeline, CPU only.
#
# The trained models and the SQLite database are NOT copied into the image:
# docker-compose mounts ./models (read-only) and ./data at run time.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# The code expects   <root>/backend, <root>/models, <root>/data   (see app/paths.py).
WORKDIR /srv/backend

COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

# Sentence splitter and lemmatiser data, so the container needs no network at run time.
RUN python -m nltk.downloader -d /usr/local/share/nltk_data punkt_tab wordnet

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
