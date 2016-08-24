#!/usr/bin/env python
import os
import requests
import statsd
import logging
import sys
import time
import re

class RabbitMonitor:
    def __init__(self):
        """
        Monitor RabbitMQ Management REST API
        """
        self.logger = logging.getLogger()
        loglevel = os.environ.get("LOG_LEVEL", logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(loglevel)

        self.statsd_host = os.environ.get("STATSD_HOST", "localhost")
        self.statsd_port = os.environ.get("STATSD_PORT", 8125)
        self.prefix = os.environ.get("PREFIX", "rabbitmq")
        self.interval = os.environ.get("INTERVAL", "30")
        self.rabbitmq_url = os.environ.get("RABBITMQ_URL", "http://localhost:15672")
        self.rabbitmq_username = os.environ.get("RABBITMQ_USERNAME", "guest")
        self.rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "guest")
        self.rabbitmq_exclude = os.environ.get("RABBITMQ_EXCLUDE", "")

        self.statsd = statsd.StatsClient(host=self.statsd_host, port=self.statsd_port, prefix=self.prefix)

        self.logger.info("Startings RabbitMQ monitor...")
        self.logger.debug("Connecting to RabbitMQ Host: %s" % self.rabbitmq_url)
        self.logger.debug("StatsD host: %s:%s" % (self.statsd_host,self.statsd_port))
        self.logger.debug("StatsD Prefix for statsd: %s" % self.prefix)
        self.logger.info("Gather stats every %s" % self.interval)

        if self.rabbitmq_exclude is not "":
            try:
                self.rabbit_regex = re.compile(self.rabbitmq_exclude)
            except:
                self.logger.info("Failed to compile Regex Exclude list [%s]" % self.rabbitmq_exclude)
                self.logger.info("\tcontinuing without exclude list")
                pass


    def _pull_stats(self):
        """
        Pull Stats from RabbitMQ Management REST API
        """
        url = "%s/api/queues" % self.rabbitmq_url
        try:
            self.logger.debug("Connecting to: %s with %s:%s" % (url, self.rabbitmq_username, self.rabbitmq_password))
            r = requests.get(url, auth=(self.rabbitmq_username, self.rabbitmq_password))
            return r.json()
        except:
            self.logger.info("Unable to connect to RabbitMQ Management API [%s]" % url)
            return False


    def _send_stats(self, stat):
        """
        Single JSON dict of Rabbit Queue, send to statsd
        """
        self.logger.debug("Sending Stats for %s - %s" % (stat['vhost'],stat['name']))
        queue_name = stat['name'].replace('.','_')
        self.statsd.gauge('%s.messages' % queue_name, stat['messages'])
        self.statsd.gauge('%s.consumers' % queue_name, stat['consumers'])
        self.statsd.gauge('%s.messages_details_rate' % queue_name, stat['messages_details']['rate'])
        self.statsd.gauge('%s.messages_ready' % queue_name, stat['messages_ready'])
        self.statsd.gauge('%s.messages_unacknowledged' % queue_name, stat['messages_unacknowledged'])
        self.statsd.gauge('%s.message_stats.ack' % queue_name, stat['message_stats']['ack'])
        try:
            self.statsd.gauge('%s.message_stats.confirm' % queue_name, stat['message_stats']['confirm'])
        except KeyError:
            pass
        try:
            self.statsd.gauge('%s.message_stats.deliver' % queue_name, stat['message_stats']['deliver'])
        except KeyError:
            pass
        try:
            self.statsd.gauge('%s.message_stats.deliver_get' % queue_name, stat['message_stats']['deliver_get'])
        except KeyError:
            pass
        try:
            self.statsd.gauge('%s.message_stats.deliver_no_ack' % queue_name, stat['message_stats']['deliver_no_ack'])
        except KeyError:
            pass
        try:
            self.statsd.gauge('%s.message_stats.get' % queue_name, stat['message_stats']['get'])
        except KeyError:
            pass
        try:
            self.statsd.gauge('%s.message_stats.get_no_ack' % queue_name, stat['message_stats']['get_no_ack'])
        except KeyError:
            pass
        try:
            self.statsd.gauge('%s.message_stats.redeliver' % queue_name, stat['message_stats']['redeliver'])
        except KeyError:
            pass
        self.statsd.gauge('%s.backing_queue_status.avg_ack_egress_rate' % queue_name, stat['backing_queue_status']['avg_ack_egress_rate'])
        self.statsd.gauge('%s.backing_queue_status.avg_ack_ingress_rate' % queue_name, stat['backing_queue_status']['avg_ack_ingress_rate'])
        self.statsd.gauge('%s.backing_queue_status.avg_egress_rate' % queue_name, stat['backing_queue_status']['avg_egress_rate'])
        self.statsd.gauge('%s.backing_queue_status.avg_ingress_rate' % queue_name, stat['backing_queue_status']['avg_ingress_rate'])


    def _parse_stats(self, stats):
        """
        Send Stats receieved from RabbitMQ Management REST API
        """
        if type(stats) is not list:
            self.logger.debug("Initial stats json was not type(list)")
            stats = list(stats)

        for stat in stats:
            self._send_stats(stat)


    def run(self):
        """
        Run Loop, gathinger statistics
        """
        while True:
            stats = self._pull_stats()

            # Catch Failure to Collect stats from RabbitMQ
            if stats:
                self._parse_stats(stats)
            else:
                self.logger.info("Failure to pull stats from RabbitMQ Management API")

            time.sleep(int(self.interval))


def main():
    rodger = RabbitMonitor()
    rodger.run()


if __name__ == '__main__':
    main()
