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
        self.rabbitmq_vhost = os.environ.get("RABBITMQ_VHOST", "/")

        self.statsd = statsd.StatsClient(host=self.statsd_host, port=self.statsd_port, prefix=self.prefix)

        self.logger.info("Startings RabbitMQ monitor...")
        self.logger.debug("Connecting to RabbitMQ Host: %s" % self.rabbitmq_url)
        self.logger.info("Collecting Stats from vhost: %s" % self.rabbitmq_vhost)
        self.logger.debug("StatsD host: %s:%s" % (self.statsd_host,self.statsd_port))
        self.logger.debug("StatsD Prefix for statsd: %s" % self.prefix)
        self.logger.info("Gather stats every %s" % self.interval)

        self.regex = False
        if self.rabbitmq_exclude is not "":
            self.logger.debug("Exclude regex: %s" % self.rabbitmq_exclude)
            try:
                self.regex = re.compile(self.rabbitmq_exclude)
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


    def _pull_rates(self):
        """
        Pull Rates from RabbitMQ Management REST API
        """
        if self.rabbitmq_vhost == '/':
            vhost = '%2f'
        else:
            vhost = self.rabbitmq_vhost

        url = "%s/api/queues/%s/?sort=message_stats.publish_details.rate&sort_reverse=true&columns=name,message_stats.publish_details.rate,message_stats.deliver_get_details.rate" % (self.rabbitmq_url, vhost)
        try:
            self.logger.debug("Connecting to: %s with %s:%s" % (url, self.rabbitmq_username, self.rabbitmq_password))
            r = requests.get(url, auth=(self.rabbitmq_username, self.rabbitmq_password))
            return r.json()
        except:
            self.logger.info("Unable to connect to RabbitMQ Management API [%s]" % url)
            return False


    def _flatten_dict(self, d):
        def items():
            for key, value in d.items():
                if isinstance(value, dict):
                    for subkey, subvalue in self._flatten_dict(value).items():
                        yield key + "." + subkey, subvalue
                else:
                    yield key, value

        return dict(items())


    def _send_stats(self, stat):
        """
        Single JSON dict of Rabbit Queue, send to statsd
        """
        self.logger.debug("Sending Stats for %s - %s" % (stat['vhost'],stat['name']))
        queue_name = stat['name'].replace('.','_')

        flat_stat = self._flatten_dict(stat)
        
        for k, v in flat_stat.items():
            if isinstance(v, list):
                self.logger.debug("Not Sending list value for %s.%s(%s)" % (queue_name, k, v))
                continue
            if isinstance(v, unicode):
                self.logger.debug("Not Sending string/unicode value for %s.%s(%s)" % (queue_name, k, v))
                continue
            self.logger.debug("Sending %s.%s: %s" % (queue_name, k, v))
            self.statsd.gauge("%s.%s" % (queue_name, k), v)


    def _send_rates(self, rate):
        """
        Single JSON dict of RabbitQueue, send to statsd
        """
        self.logger.debug("Sending Rates for %s" % (rate['name']))
        queue_name = rate['name'].replace('.','_')

        flat_rate = self._flatten_dict(rate)

        for k, v in flat_rate.items():
            if isinstance(v, list):
                self.logger.debug("Not Sending list value for %s.%s(%s)" % (queue_name, k, v))
                continue
            if isinstance(v, unicode):
                self.logger.debug("Not Sending string/unicode value for %s.%s(%s)" % (queue_name, k, v))
                continue
            self.logger.debug("Sending %s.%s: %s" % (queue_name, k, v))
            self.statsd.gauge("%s.%s" % (queue_name, k), v)


    def _parse_stats(self, stats):
        """
        Send Stats receieved from RabbitMQ Management REST API
        """
        if type(stats) is not list:
            self.logger.debug("Initial stats json was not type(list)")
            self.logger.debug(stats)
            stats = list(stats)

        for stat in stats:
            if self.regex:
                # If regex does not match queue name, send stats
                if self.regex.match(stat['name']) is None:
                    self._send_stats(stat)
                else:
                    self.logger.debug("Excluded Queue [%s] because of regex: '%s'" % (stat['name'],self.rabbitmq_exclude))
            else:
                self._send_stats(stat)


    def _parse_rates(self, rates):
        """
        Send Rates received from RabbitMQ Management REST API
        """
        if type(rates) is not list:
            self.logger.debug("Initial rates json was not type(list)")
            self.logger.debug(rates)
            rates = list(rates)

        for rate in rates:
            if self.regex:
                # If regex does not match queue name, send rates
                if self.regex.match(rate['name']) is None:
                    self._send_rates(rate)
                else:
                    self.logger.debug("Exclude Queue [%s] because of regex: '%s'" % (rate['name'],self.rabbitmq_exclude))
            else:
                self._send_rates(rate)


    def run(self):
        """
        Run Loop, gathinger statistics
        """
        while True:
            self.logger.info("Starting Stat run of %s" % self.rabbitmq_url)
            stats = self._pull_stats()

            # Catch Failure to Collect stats from RabbitMQ
            if stats:
                self._parse_stats(stats)
            else:
                self.logger.info("Failure to pull stats from RabbitMQ Management API")
            
            # Pull Rates
            #self.logger.info("Starting Rates run of %s" % self.rabbitmq_url)
            #rates = self._pull_rates() 
            
            # Catch Failure to Collect rates from RabbitMQ
            #if rates:
            #    self._parse_rates(rates)
            #else:
            #    self.logger.info("Failure to pull rates from RabbitMQ Management API")

            time.sleep(int(self.interval))


def main():
    rodger = RabbitMonitor()
    rodger.run()


if __name__ == '__main__':
    main()
