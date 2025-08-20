#!/bin/ash
set -e
while true
do
    echo "Calling duckdns..."
    echo url=$DUCKDNS_URL | curl --head --silent --fail --config -
    echo -e "\nCalling tickbeat..."
    curl -X POST -H "Authorization: Bearer $DUCKDNS_TICKBEAT_SECRET" $DUCKDNS_TICKBEAT_URL
    echo -e "OK"
    echo "Sleeping..."
    sleep 300
done
