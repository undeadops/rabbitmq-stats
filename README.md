## RabbitMQ Stats

Query RabbitMQ Management API send stats to StatsD host

### Running 

I run this script locally like:

    RABBITMQ_USERNAME=bugsbunny RABBITMQ_PASSWORD=mypassword LOG_LEVEL=DEBUG RABBITMQ_EXCLUDE='amq.gen-*' python rabbitmq-stats.py


Of coarse this depends on a local RabbitMQ server.  You can start one up with docker like this:

    docker run -d --hostname my-rabbit --name some-rabbit -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=bugsbunny -e RABBITMQ_DEFAULT_PASS=mypassword rabbitmq:3-management

This will start a docker container of RabbitMQ for testing

## Docker

I run this script in a Docker container in production.  I launch it with a command similar to

    docker run -d --hostname rabbitmq-stats \ 
                  --name rabbitmq-stats-stage \
                  -e RABBITMQ_URL: http://rabbit-server.example.com:15672 \
                  -e RABBITMQ_USERNAME: bugsbunny \
                  -e RABBITMQ_PASSWORD: mypassword \
                  -e RABBITMQ_EXCLUDE: 'amq\.gen-*' \
                  -e INTERVAL: 25 \
                  -e PREFIX: rabbitmq-stage \
                  -e STATSD_HOST: statsd.example.com \
                  -e STATSD_PORT: 8125 \
                  undeadops/rabbitmq-stats

                  
It currently doesn't have a /healthz endpoint (!?!?... I know right... I will promise)

Pull-Requests welcome for more stats to send along

