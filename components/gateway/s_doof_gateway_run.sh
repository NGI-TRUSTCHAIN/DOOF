#!/bin/bash

ROOT_DIR="/home/ecosteer/NGI-TRUSTCHAIN/DOOF"
VENV_DIR="/home/ecosteer/virtualenv"
CONFHOME="/home/ecosteer/conf"

cd ${ROOT_DIR}/components/gateway/
pwd 

source ${DOP_VENV_DIR}/dop/bin/activate
source env.sh

uwsgi --uid ecosteer --https 0.0.0.0:5443,$CONFHOME/ssl/cert.pem,$CONFHOME/ssl/key.pem \
    --wsgi-file doof_gateway_api.py --set conf=${CONFHOME}/gateway/gateway_config.template \
    --callable app --processes 2 --threads 2 --lazy-apps

