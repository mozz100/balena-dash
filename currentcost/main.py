# https://github.com/tomtaylor/currentcost/blob/master/currentcost.py

import csv
import datetime
import logging
import os
import signal
import sys
import time
from xml.etree.cElementTree import fromstring
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

import requests
import serial

log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.DEBUG))

logging.info("Opening serial port")
serial_port = serial.Serial('/dev/ttyUSB0', 57600, timeout=5.0)
logging.info("Serial port opened")

MOZZWORLD_AUTH_TOKEN = os.environ.get("MOZZWORLD_AUTH_TOKEN")
MOZZWORLD_URL_CURRENTCOST = os.environ.get("MOZZWORLD_URL_CURRENTCOST")

INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "https://eu-central-1-1.aws.cloud2.influxdata.com")
INFLUXDB_MEASUREMENT_BATCH = int(os.environ.get("INFLUXDB_MEASUREMENT_BATCH", "10"))
CURRENTCOST_TICKBEAT_URL = os.environ["CURRENTCOST_TICKBEAT_URL"]
CURRENTCOST_TICKBEAT_SECRET = os.environ["CURRENTCOST_TICKBEAT_SECRET"]

class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return datetime.timedelta(0)


def utc_now_string():
    return datetime.datetime.now(UTC()).strftime('%Y-%m-%dT%H:%M:%SZ')

def signal_term_handler(signal, frame):
    logging.info("signal_term_handler. Exiting.")
    sys.exit(0)

def send_to_influxdb(measurements):
    logging.info("send_to_influxdb: %s", measurements)
    sequence = []
    for atime, watts in measurements:
        ts = str(int(atime.timestamp() * 1000000000))
        line = f"power watts={watts} {ts}"
        sequence.append(line)
        logging.debug("appended to sequence: %s", line)
    try:
        logging.info("Influx db starting")
        with InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        ) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, sequence)
            logging.info("Influx db write complete")
        # Hit tickbeat
        logging.info("Hitting tickbeat...")
        requests.post(CURRENTCOST_TICKBEAT_URL, headers={"Authorization": f"Bearer {CURRENTCOST_TICKBEAT_SECRET}"})
        logging.info("Hit tickbeat")
    except Exception as e:
        logging.exception("Bad thing happened: %s", e)

signal.signal(signal.SIGTERM, signal_term_handler)

measurements = []
while True:
    msg = serial_port.readline()
    logging.debug("msg: %s", msg)
    if len(msg) == 0:
        logging.info("Empty msg")
        continue
    if not msg:
        raise ValueError('Time out')
    xml = fromstring(msg)
    if xml.tag != 'msg':
        logging.debug("xml.tag was not msg")
        continue
    if xml.find('hist'):
        logging.debug("hist found")
        continue
    watts = int(xml.find('ch1').find('watts').text)
    timestamp = utc_now_string()
    row = [timestamp, watts]
    measurements.append([datetime.datetime.now(UTC()), watts])
    logging.info("row %s", row)
    try:
        resp = requests.post(
            url=MOZZWORLD_URL_CURRENTCOST,
            headers={"Authorization": f"Token {MOZZWORLD_AUTH_TOKEN}"},
            json={
                "series": 2,  # TODO series by key
                "value": watts,
                "timestamp": timestamp,
            }
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        logging.exception("HTTPError: %s", e)
    
    if len(measurements) >= INFLUXDB_MEASUREMENT_BATCH:
        send_to_influxdb(measurements)
        measurements = []
