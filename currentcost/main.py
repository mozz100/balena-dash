# https://github.com/tomtaylor/currentcost/blob/master/currentcost.py

import csv
import datetime
import os
import signal
import sys
import time
from xml.etree.cElementTree import fromstring
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

import requests
import serial

serial = serial.Serial('/dev/ttyUSB0', 57600)
MOZZWORLD_AUTH_TOKEN = os.environ.get("MOZZWORLD_AUTH_TOKEN")
MOZZWORLD_URL_CURRENTCOST = os.environ.get("MOZZWORLD_URL_CURRENTCOST")

INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "https://eu-central-1-1.aws.cloud2.influxdata.com")
INFLUXDB_MEASUREMENT_BATCH = int(os.environ.get("INFLUXDB_MEASUREMENT_BATCH", "10"))

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
    sys.exit(0)

def send_to_influxdb(measurements):
    print("send_to_influxdb")
    print(measurements)
    sequence = []
    for atime, watts in measurements:
        ts = atime.timestamp() * 1000000000
        line = f"power watts={watts} {ts}"
        sequence.append(line)
        print(line)
    try:
        with InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        ) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, sequence)
    except Exception as e:
        print(e)

signal.signal(signal.SIGTERM, signal_term_handler)

measurements = []
while True:
    msg = serial.readline()
    if not msg:
        raise ValueError('Time out')
    xml = fromstring(msg)
    if xml.tag != 'msg':
        continue
    if xml.find('hist'):
        continue
    watts = int(xml.find('ch1').find('watts').text)
    timestamp = utc_now_string()
    row = [timestamp, watts]
    measurements.append([datetime.datetime.now(UTC()), watts])
    print(row)
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
    except requests.HTTPError as e:
        print("HTTPError", e)
    
    if len(measurements) >= INFLUXDB_MEASUREMENT_BATCH:
        send_to_influxdb(measurements)
        measurements = []