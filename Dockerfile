FROM python:3.10

RUN apt update && apt install postgresql-client -y

RUN pip install psycopg==3.1.13

RUN mkdir /src
WORKDIR /src

