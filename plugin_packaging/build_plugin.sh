#!/bin/bash

current=`pwd`
mkdir -p /tmp/topicSHARK/
cp -R ../topicSHARK /tmp/topicSHARK/
cp ../setup.py /tmp/topicSHARK/
cp ../main.py /tmp/topicSHARK
cp ../wordfilter.txt /tmp/topicSHARK
cp ../loggerConfiguration.json /tmp/topicSHARK
cp * /tmp/topicSHARK/
cd /tmp/topicSHARK/

tar -cvf "$current/topicSHARK_plugin.tar" --exclude=*.tar --exclude=build_plugin.sh --exclude=*/tests --exclude=*/__pycache__ --exclude=*.pyc *
