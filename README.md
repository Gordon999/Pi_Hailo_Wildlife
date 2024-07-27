# Pi_Hailo_Wildlife
Pi5 + Hailo HAT + PI Camera to capture Wildlife videos

Note I use a 8GB Pi5, and save frames to RAM, if you expect a lot of detections, and hence long videos this may fill the ram and at present l haven't 
any detection to stop this. It could be added if required.

Captures 640x640 images and makes .mp4 videos

Change line 94 to suit your required detections .... if (label == "cat" and confidence > 0.35) or (label == "bear" and confidence > 0.35):

Note in line 259 the width and height are set for a Pi GS camera, you may need to change to suit other cameras... 
  source_element += f"video/x-raw, format={self.network_format}, width=1280, height=1088 ! "

Runs a pre-capture buffer of approx 2 seconds

Copy detection_001.py into /home/USERNAME/hailo-rpi5-examples/basic_pipelines/detection_001.py

Videos saved in /home/USERNAME/Videos

Edit start_cam.sh to suit your USERNAME, eg change gt64bw to your USERNAME

Run with ./start_cam.sh

Note it is set to shutdown at 21:00, if clock synced, see line 19 sd_hour = 21

Probably needs the Active Cooler fitted to the Pi5, l change the fan to start at 60degC.

if you want to crop the image to make use of the full 640x640...

def get_pipeline_string(self):
if (self.source_type == "rpi"):
source_element = f"libcamerasrc name=src_0 ! "
source_element += f"video/x-raw, format={self.network_format}, width=1280, height=1088 ! "
source_element += QUEUE("queue_src_scale")
source_element += f"videocrop top=0 left=96 right=96 bottom=0 ! "
source_element += f"videoscale ! "
source_element += f"video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height}, framerate=25/1 ! "

to get a 640x640 crop from the centre of the image change to top=224 left=320 right=320 bottom=224
