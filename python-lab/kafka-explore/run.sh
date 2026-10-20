#!/bin/bash

source venv/bin/activate

# Use a fixed broker port; 8082 is Kafka REST, not the client port.
confluent local kafka start

echo "Waiting for Kafka core services to report 'UP' status..."
TIMEOUT=45
ELAPSED=0

# Loop until the status output explicitly states the service is UP
until confluent local kafka topic list >/dev/null 2>&1; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "Error: Kafka services failed to reach 'UP' state within $TIMEOUT seconds."
        exit 1
    fi
done

confluent local kafka topic create test-topic

python3 consumer.py