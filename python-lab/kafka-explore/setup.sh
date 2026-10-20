#!/bin/bash

echo '--------------------  creating venv  --------------------'
python3 -m venv venv
wait

# Comment this section if you already have the kafka cluster running in your local machine
# Or you can also run the kafka cluster in a docker container. 
# Or you can connect to a remote/cloud kafka cluster.
echo '--------------------  Installing Confluent CLI for a local Kafka Cluster --------------------'
sudo apt install curl gnupg
wait
sudo mkdir -p /etc/apt/keyrings
curl https://packages.confluent.io/confluent-cli/deb/archive.key | sudo gpg --dearmor -o /etc/apt/keyrings/confluent-cli.gpg
sudo chmod go+r /etc/apt/keyrings/confluent-cli.gpg
wait
echo "deb [signed-by=/etc/apt/keyrings/confluent-cli.gpg] https://packages.confluent.io/confluent-cli/deb stable main" | sudo tee /etc/apt/sources.list.d/confluent-cli.list >/dev/null
wait
sudo apt update
wait
sudo apt install confluent-cli
wait
# Kafka REST Port : 8082
# Plaintext Ports : 44919
# To continue your Confluent Local experience, run confluent local kafka topic create <topic> and confluent local kafka topic produce <topic>.

sudo apt autoremove
wait

echo '-------------  install project requirements  ------------'
source venv/bin/activate && pip install -r requirements.txt
wait