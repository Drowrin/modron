FROM python:3.11-alpine

RUN apk add build-base

WORKDIR /modron

COPY . .
RUN mv ./example.config.yml ./config.yml

RUN pip install .

CMD ["python", "-m", "modron", "-c", "/modron/config.yml"]
