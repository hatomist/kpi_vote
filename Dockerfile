FROM python:3.9-buster

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

RUN apt update
RUN apt install libzbar0 libgl1 -y

COPY requirements.txt .
RUN pip install -r requirements.txt

ENV PYTHONBUFFERED 1
COPY ./*.py ./
COPY ./translations ./translations
