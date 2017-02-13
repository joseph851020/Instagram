#!/bin/bash
# Executes all necessary software for development
# Elasticsearch
# Redis-server
# kibana
# Celery worker
# Requires to execute the virtualenvironment first

trap killgroup EXIT

killgroup(){
  echo killing...
  kill $(jobs -p)
}

redis-server &
celery -A master worker -l debug &
celery -A master beat -l debug &
wait
echo "done"
