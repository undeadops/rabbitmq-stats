FROM undeadops/alpine-python:3.4

MAINTAINER Mitch Anderson <mitch@metauser.net>

RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD rabbitmq-stats.py /app

CMD ["/usr/bin/python","rabbitmq-stats.py"]