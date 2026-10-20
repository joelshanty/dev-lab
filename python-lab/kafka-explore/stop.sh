#!/bin/bash
confluent local kafka stop
wait
confluent local destroy
wait
docker network prune -f