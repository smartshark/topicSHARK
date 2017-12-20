#!/bin/sh
NEW_UUID=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
mkdir "/dev/shm/$NEW_UUID"

COMMAND="python3.5 ${1}/main.py --db-database ${4} --db-hostname ${5} --db-port ${6} --project-name ${8} --filter ${9} --output /dev/shm/$NEW_UUID"

if [ ! -z ${2+x} ] && [ ${2} != "None" ]; then
COMMAND="$COMMAND --db-user ${2}"
fi

if [ ! -z ${3+x} ] && [ ${3} != "None" ]; then
COMMAND="$COMMAND --db-password ${3}"
fi

if [ ! -z ${7+x} ] && [ ${7} != "None" ]; then
COMMAND="$COMMAND --db-authentication ${7}"
fi

if [ ! -z ${10+x} ] && [ ${10} != "None" ]; then
COMMAND="$COMMAND --K ${10}"
fi

if [ ! -z ${11+x} ] && [ ${11} != "None" ]; then
COMMAND="$COMMAND --filter_language ${11}"
fi

if [ ! -z ${12+x} ] && [ ${12} != "None" ]; then
COMMAND="$COMMAND --filter_project ${12}"
fi

if [ ! -z ${13+x} ] && [ ${13} != "None" ]; then
COMMAND="$COMMAND --issue ${13}"
fi

if [ ! -z ${14+x} ] && [ ${14} != "None" ]; then
COMMAND="$COMMAND --issue_comments ${14}"
fi

if [ ! -z ${15+x} ] && [ ${15} != "None" ]; then
COMMAND="$COMMAND --messages ${15}"
fi

if [ ! -z ${16+x} ] && [ ${16} != "None" ]; then
COMMAND="$COMMAND --passes ${16}"
fi

if [ ! -z ${17+x} ] && [ ${17} != "None" ]; then
COMMAND="$COMMAND --debug ${17}"
fi


$COMMAND

rm -rf "/dev/shm/$NEW_UUID"
