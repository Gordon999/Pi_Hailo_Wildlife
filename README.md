# Pi_Hailo_Wildlife
Pi5 + Hailo to capture Wildlife videos

Captures 640x640 images and makes .mp4 videos

Change line 94 to suit your detections .... if (label == "cat" and confidence > 0.35) or (label == "bear" and confidence > 0.35):

Note in line 259 the width and height are set for a Pi GS camera, you may need to change to suit other cameras

source_element += f"video/x-raw, format={self.network_format}, width=1280, height=1088 ! "

Edit start_cam.sh to suit your user name, eg change gt64bw

run with ./start_cam.sh

Runs a pre-capture buffer of approx 2 seconds

copy detection_001.py into /home/USERNAME/hailo-rpi5-examples/basic_pipelines/detection_001.py

Videos saved in /home/USERNAME/Videos
