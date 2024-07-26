#!/bin/bash
cd /home/gt64bw/hailo-rpi5-examples
source setup_env.sh
sleep 2
/usr/bin/python /home/gt64bw/hailo-rpi5-examples/basic_pipelines/detection_008x5.py --input rpi -u
