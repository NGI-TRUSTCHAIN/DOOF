#!/bin/bash

ROOT_DIR="/home/ecosteer/NGI-TRUSTCHAIN/DOOF"
VENV_DIR="/home/ecosteer/virtualenv"
CONFHOME="/home/ecosteer/conf"

cd ${ROOT_DIR}/components/gateway/
pwd 

source ${VENV_DIR}/dop/bin/activate
source env.sh

uwsgi --uid ecosteer --http 0.0.0.0:2783 \
    --wsgi-file doof_gateway_api.py --set conf=${CONFHOME}/gateway/gateway_config.template \
    --callable app --processes 2 --threads 2 --lazy-apps

