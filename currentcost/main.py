# https://github.com/tomtaylor/currentcost/blob/master/currentcost.py

import csv
import datetime
import os
import signal
import sys
import time
from xml.etree.cElementTree import fromstring

import requests
import serial

serial = serial.Serial('/dev/ttyUSB0', 57600)
MOZZWORLD_AUTH_TOKEN = os.environ.get("MOZZWORLD_AUTH_TOKEN")
MOZZWORLD_URL_CURRENTCOST = os.environ.get("MOZZWORLD_URL_CURRENTCOST")

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

signal.signal(signal.SIGTERM, signal_term_handler)

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
