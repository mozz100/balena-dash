#!/bin/ash
set -e
while true
do
    echo "Calling duckdns..."
    echo url=$DUCKDNS_URL | curl -s -k -K -
    echo -e "\nCalling tickbeat..."
    curl -s -d "" $DUCKDNS_TICKBEAT_URL
    echo -e "OK"
    echo "Sleeping..."
    sleep 300
done
