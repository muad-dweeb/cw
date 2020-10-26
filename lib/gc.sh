#!/bin/bash

find /home/ubuntu/muad-dweeb/cw/data/*$(date +%Y)*.csv -mtime +10 -type f -delete
