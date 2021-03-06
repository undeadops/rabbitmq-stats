FROM undeadops/alpine-python:3.4

MAINTAINER Mitch Anderson <mitch@metauser.net>

RUN mkdir -p /app
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY rabbitmq-stats.py /app

CMD ["/usr/bin/python","rabbitmq-stats.py"]
