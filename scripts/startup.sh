#!/bin/bash

if [ -n "$PORT" ]; then
    echo "Running Python SimpleHTTPServer on Port $PORT"
    /usr/bin/python -m SimpleHTTPServer $PORT &
fi

echo "Starting RabbitMQ Stats Collector"
/usr/bin/python rabbitmq-stats.py
