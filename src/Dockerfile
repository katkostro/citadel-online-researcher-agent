# syntax=docker/dockerfile:1

FROM python:3.13.5-slim-bookworm

WORKDIR /code

COPY . .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

EXPOSE 50505

CMD ["gunicorn", "--config", "gunicorn_sk_conf.py", "main_sk:app"]