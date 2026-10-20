# Kafka Explore

A small Python example using Confluent Kafka. The producer sends ten sample events to `test-topic`; the consumer prints events from that topic.

## Requirements

- Linux with Python 3
- Docker running
- Confluent CLI

On Debian or Ubuntu, `setup.sh` creates a virtual environment, installs the Confluent CLI with `apt`, and installs the Python dependency from `requirements.txt`. It uses `sudo` for the system package installation.
Comment the kafka cluster/cli installation section if you already have the kafka cluster running in your local machine or you plan to run the kafka cluster in a docker container or you can connect to a remote cloud kafka cluster.

## Setup

From this directory, run:

```bash
./setup.sh
```
run this only for the first time.

## Run

Run the Kafka startup script from this directory:

```bash
./run.sh
```

The script starts Confluent Local with the Kafka broker on port `9092`, waits for Kafka to respond, creates `test-topic`, and starts and run the consumer. The consumer stays running and prints messages as they arrive.

In a second terminal, from this same directory, activate the virtual environment and run the producer:

```bash
source venv/bin/activate
python3 producer.py
```

The producer sends ten events. The consumer should print them. Press `Ctrl+C` in the first terminal to stop the consumer.

The Python clients connect to `localhost:9092`. Port `8082` is the Kafka REST endpoint, not the broker endpoint.

## Stop Kafka

After stopping the consumer, stop the local Kafka service with:

```bash
confluent local kafka stop
```

`stop.sh` also runs `confluent local destroy` and `docker network prune -f`. That removes the local Confluent data and prunes every unused Docker network on the machine, so use it only if that cleanup is intended.