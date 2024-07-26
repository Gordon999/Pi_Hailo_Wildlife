# Pi_Hailo_Wildlife
Pi5 + Hailo HAT + PI Camera to capture Wildlife videos

Note I use a 8GB Pi5, and save frames to RAM.

Captures 640x640 images and makes .mp4 videos

Change line 94 to suit your required detections .... if (label == "cat" and confidence > 0.35) or (label == "bear" and confidence > 0.35):

Note in line 259 the width and height are set for a Pi GS camera, you may need to change to suit other cameras

source_element += f"video/x-raw, format={self.network_format}, width=1280, height=1088 ! "

Runs a pre-capture buffer of approx 2 seconds

Copy detection_001.py into /home/USERNAME/hailo-rpi5-examples/basic_pipelines/detection_001.py

Videos saved in /home/USERNAME/Videos

Edit start_cam.sh to suit your USERNAME, eg change gt64bw to your USERNAME

Run with ./start_cam.sh

Note it is set to shutdown at 21:00, if clock synced, see line 19 sd_hour = 21

Probably needs the Active Cooler fitted to the Pi5, l change the fan to start at 60degC.
