#!/usr/bin/env bash

mkdir /tmp/data1 /tmp/data2
psql -U test -c "CREATE TABLESPACE data1 LOCATION '/tmp/data1'"
psql -U test -c "CREATE TABLESPACE data2 LOCATION '/tmp/data2'"
