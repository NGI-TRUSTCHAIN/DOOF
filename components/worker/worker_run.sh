#!/bin/bash

ROOT_DIR="/home/ecosteer/NGI-TRUSTCHAIN/DOOF"
VENV_DIR="/home/ecosteer/virtualenv"
CONFHOME="/home/ecosteer/conf"

cd ${ROOT_DIR}/components/worker

pwd

source ${VENV_DIR}/dop/bin/activate
source env.sh

#       BEFORE STARTING the worker components, the following
#       services must be up and running:
#       1)      rabbit-mq (use the docker image)
#       2)      mqtt (use the docker image)
#       3)      postgres (daemon)
#       4)      blockchain

python doof_worker.py -c ${CONFHOME}/worker/worker_config.template 
