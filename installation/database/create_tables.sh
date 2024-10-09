#!/bin/sh

if [ $# != 3 ]
then
    echo "Please supply a database name and a database user"
    echo "Usage: create_tables.sh DB_NAME DB_USER DB_PASSWORD"
    exit 1
fi

DB_NAME=$1
DB_USER=$2
DB_PASSWORD=$3

#sudo -u postgres createdb $DB_NAME
#cd ~/installation/

sudo -u ${DB_USER} psql -d ${DB_NAME} -f create_tables.sql
sudo -u ${DB_USER} psql -d ${DB_NAME} -f create_rif_tables.sql
#       in order to check if the db DB_NAME has been created
#       and to check if the user DB_USER has been created too,
#       use the following commands
#       sudo -u DB_USER psql            [starts psql as user]
#       \l                              [shows all the available dbs]
#       \c DB_NAME                      [connects current user to the db]
#       \dt                             [show tables, etc]
#
#       for more details see the following tutorial
#       https://chartio.com/resources/tutorials/how-to-list-databases-and-tables-in-postgresql-using-psql/

#       it is assumed that the port postgres is listening to is 5432
#       please check config file
#       /etc/postgresql/10/main/postgresql.conf
#       read the following tutorial if conf needs to be changed
#       https://www.jamescoyle.net/how-to/3019-how-to-change-the-listening-port-for-postgresql-database

