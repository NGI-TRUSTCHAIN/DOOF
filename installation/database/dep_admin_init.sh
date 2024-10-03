#!/bin/bash 


if [ $# != 3 ]
then
    echo "Please supply a database user, a database name and the admin username/unique identifier"
    echo "Usage: dep_admin_init.sh DB_USER DB_NAME ADMIN"
    exit 1
fi

DB_USER=$1
DB_NAME=$2
ADMIN=$3


cp dep_admin_init.template.sql dep_admin_init.sql
sed -i "s/_admin_/${ADMIN}/g" dep_admin_init.sql 


sudo -u ${DB_USER} psql -d ${DB_NAME} -f dep_admin_init.sql
