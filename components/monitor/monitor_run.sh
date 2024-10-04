#!/bin/bash

ROOT_DIR="/home/ecosteer/NGI-TRUSTCHAIN/DOOF"
VENV_DIR="/home/ecosteer/virtualenv"
CONFHOME="/home/ecosteer/conf"

cd ${ROOT_DIR}/components/monitor

pwd

source ${VENV_DIR}/dop/bin/activate
source env.sh

#	BEFORE STARTING 
#	the monitor component needs availability of 
#	a)	blockchain service 
#	b)	message queueing (rabbit-mq)

#	WARNING
#	the monitor allows the idx=BLOCKNUM option
#	if the idx of the last processed block is not specified
#	then it will be used the index previously saved, stored
#	in the file specified within the configuration file
#	based on the used conf file, the lastindex file is
#	'monitor.lastindex'
#	if you want to start from 0 block you can specify idx=0
#	if you delete the index file then the monitor will start
#	processing the last available block
python monitor.py ${CONFHOME}/monitor/monitor_config.template



