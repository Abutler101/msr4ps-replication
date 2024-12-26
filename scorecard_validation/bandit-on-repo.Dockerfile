FROM python:3.12-alpine

RUN apk add --no-cache git
RUN pip install --upgrade pip
RUN pip install bandit

COPY target-repo /target-repo

ENTRYPOINT ["bandit"]