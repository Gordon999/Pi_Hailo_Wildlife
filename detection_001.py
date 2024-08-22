import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import argparse
import multiprocessing
import numpy as np
import setproctitle
import cv2
import time
import datetime
import shutil
import os
import glob
import hailo
from hailo_common_funcs import get_numpy_from_buffer, disable_qos
from hailo_rpi_common import get_default_parser, QUEUE, get_caps_from_pad, GStreamerApp, app_callback_class
from gpiozero import LED

# v0.02

# set variables
vid_length = 10  # seconds
mp4_timer  = 10  # seconds
pre_frames = 90  # frames
led        = 21  # record led gpio

# shutdown time
sd_hour = 20
sd_mins = 30
auto_sd = 0  # set to 1 to shutdown at set time

# -----------------------------------------------------------------------------------------------
# User defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# iheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42 # new variable example
            
    def new_function(self): # new function example
        return "The meaning of life is: "

# Create an instance of the class
user_data = user_app_callback_class()

# -----------------------------------------------------------------------------------------------
# User defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    global rec_led,synced,h_user,m_user,sd_hour,sd_mins,b_count,f_count,auto_sd,record,start,timestamp,pre_frames,user,vid_length,start2,mp4_timer
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
        
    # using the user_data to count the number of frames
    user_data.increment()
    
    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if format is not None and width is not None and height is not None:
        # get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)
    # get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    # parse the detections
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        #print(label,confidence)
        if (label == "cat" and confidence > 0.35) or (label == "bear" and confidence > 0.35) or (label == "clock" and confidence > 0.35):
            # start recording on detection
            if record == 0:
                record = 1
                rec_led.on()
                now = datetime.datetime.now()
                timestamp = now.strftime("%y%m%d%H%M%S")
            start  = time.monotonic()
            start2 = time.monotonic()
                 
    # stop recording if exceeded required video length and no detections
    if record == 1 and time.monotonic() - start > vid_length:
        start2 = time.monotonic()
        start  = time.monotonic()
        record = 0
        rec_led.off()
        b_count = 0
        f_count = 0
        # rename buffer frames
        pics = glob.glob('/run/shm/buffer*.jpg')
        pics.sort(reverse = False)
        frames = 0
        for x in range(0,len(pics)):
            frame = "00000" + str(frames)
            os.rename(pics[x],'/run/shm/' + timestamp + "_" + str(frame[-5:]) + '.jpg')
            frames +=1
        # rename captured frames
        pics = glob.glob('/run/shm/frames*.jpg')
        pics.sort(reverse = False)
        for x in range(0,len(pics)):
            frame = "00000" + str(frames)
            os.rename(pics[x],'/run/shm/' + timestamp + "_" + str(frame[-5:]) + '.jpg')
            frames +=1

    if record == 0: # add to circular buffer
        b_count +=1
        f_count = 0
        count = "000000" + str(b_count)
        frame2 = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("/run/shm/buffer_" + str(count[-6:]) + ".jpg",frame2)
        pics = glob.glob('/run/shm/buffer*.jpg')
        pics.sort(reverse = True)
        # delete oldest jpeg if > pre_frames set
        jcount = len(pics)
        if jcount > pre_frames:
            os.remove(pics[jcount - 1])
        
    elif record == 1: # record frames
        f_count +=1
        count = "00000" + str(f_count)
        frame2 = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("/run/shm/frames_" + str(count[-5:]) + ".jpg",frame2)
        
    if time.monotonic() - start2 > mp4_timer and record == 0: # make mp4s if not recording for mp4_timer seconds
        start2 = time.monotonic()
        rec_led.off()
        mpics = glob.glob('/run/shm/2*.jpg')
        mpics.sort(reverse = False)
        z = ""
        outvids = []
        for x in range(0,len(mpics)):
            npics = mpics[x].split("/")
            if npics[len(npics) - 1][:-10] != z:
                z = npics[len(npics) - 1][:-10]
                outvids.append(z)
        for y in range(0,len(outvids)):
            timestamp = outvids[y]
            if not os.path.exists("/home/" + user + "/Videos/" + timestamp + "_1.mp4"):
                pics = glob.glob('/run/shm/' + timestamp + '*.jpg')
                pics.sort(reverse = False)
                cmd = 'ffmpeg -framerate 25 -f image2 -i /run/shm/' + timestamp + '_%5d.jpg '
                # annotate date and time
                year = 2000 + int(timestamp[0:2])
                mths = int(timestamp[2:4])
                days = int(timestamp[4:6])
                hour = int(timestamp[6:8])
                mins = int(timestamp[8:10])
                secs = int(timestamp[10:12])
                cmd += '-vf drawtext="fontsize=15:fontfile=/usr/share/fonts/truetype/freefont/FreeSerif.ttf:\ '
                cmd += "timecode='  " +str(hour) +"\:" + str(mins) + "\:" + str(secs) + "\:00':rate=25:text=" + str(days)+"/"+str(mths)+"/"+str(year)+"--"
                cmd += ":fontsize=20:fontcolor='white@0.8':\ "
                cmd += 'boxcolor=black@0.0:box=1:x=10:y=580" '
                # destination for mp4 output
                cmd += "/home/" + user + "/Videos/" + timestamp + "_1.mp4"
                # run command
                os.system(cmd)
        for y in range(0,len(mpics)):
            os.remove(mpics[y])
        # check if clock synchronised
        if "System clock synchronized: yes" in os.popen("timedatectl").read().split("\n"):
            synced = 1
        else:
            synced = 0
        # check current hour and shutdown
        now = datetime.datetime.now()
        sd_time = now.replace(hour=sd_hour, minute=sd_mins, second=0, microsecond=0)
        if now >= sd_time and time.monotonic() - startup > 300 and synced == 1 and auto_sd == 1:
            # move mp4s to USB if present
            USB_Files  = []
            USB_Files  = (os.listdir(m_user))
            if len(USB_Files) > 0:
                usedusb = os.statvfs(m_user + "/" + USB_Files[0] + "/")
                USB_storage = ((1 - (usedusb.f_bavail / usedusb.f_blocks)) * 100)
            if len(USB_Files) > 0 and USB_storage < 90:
                Videos = glob.glob(h_user + '/Videos/*.mp4')
                Videos.sort()
                for xx in range(0,len(Videos)):
                    movi = Videos[xx].split("/")
                    if not os.path.exists(m_user + "/" + USB_Files[0] + "/Videos/" + movi[4]):
                        shutil.move(Videos[xx],m_user + "/" + USB_Files[0] + "/Videos/")
            time.sleep(5)
            # shutdown
            os.system("sudo shutdown -h now")

    return Gst.PadProbeReturn.OK

#-----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------
# This class inherits from the hailo_rpi_common.GStreamerApp class

class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, args, user_data):
        # Call the parent class constructor
        super().__init__(args, user_data)
        # Additional initialization code can be added here
        # Set Hailo parameters these parameters should be set based on the model used
        self.batch_size = 2
        self.network_width = 640
        self.network_height = 640
        self.network_format = "RGB"
        self.default_postprocess_so = os.path.join(self.postprocess_dir, 'libyolo_hailortpp_post.so')

        # Set the HEF file path based on the network
        if args.network == "yolov6n":
            self.hef_path = os.path.join(self.current_path, '../resources/yolov6n.hef')
        elif args.network == "yolov8s":
            self.hef_path = os.path.join(self.current_path, '../resources/yolov8s_h8l.hef')
        elif args.network == "yolox_s_leaky":
            self.hef_path = os.path.join(self.current_path, '../resources/yolox_s_leaky_h8l_mz.hef')
        else:
            assert False, "Invalid network type"

        self.app_callback = app_callback
    
        nms_score_threshold = 0.3 
        nms_iou_threshold = 0.45
        self.thresholds_str = f"nms-score-threshold={nms_score_threshold} nms-iou-threshold={nms_iou_threshold} output-format-type=HAILO_FORMAT_TYPE_FLOAT32"

        # Set the process title
        setproctitle.setproctitle("Hailo Detection App")

        self.create_pipeline()

    def get_pipeline_string(self):
        if (self.source_type == "rpi"):
            source_element = f"libcamerasrc name=src_0 ! " 
            source_element += f"video/x-raw, format={self.network_format}, width=1280, height=1088 ! " # dimensions for Pi GS camera
            source_element += QUEUE("queue_src_scale")
            # source_element += f"videocrop top=0 left=96 right=96 bottom=0 ! " # crop to square format
            source_element += f"videoscale ! "
            source_element += f"video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height}, framerate=25/1 ! "
        
        elif (self.source_type == "usb"):
            source_element = f"v4l2src device={self.video_source} name=src_0 ! "
            source_element += f"video/x-raw, width=640, height=480, framerate=25/1 ! "
        else:  
            source_element = f"filesrc location={self.video_source} name=src_0 ! "
            source_element += QUEUE("queue_dec264")
            source_element += f" qtdemux ! h264parse ! avdec_h264 max-threads=2 ! "
            source_element += f" video/x-raw,format=I420 ! "
        source_element += QUEUE("queue_scale")
        source_element += f" videoscale n-threads=2 ! "
        source_element += QUEUE("queue_src_convert")
        source_element += f" videoconvert n-threads=3 name=src_convert qos=false ! "
        source_element += f"video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height}, pixel-aspect-ratio=1/1 ! "
        
        
        pipeline_string = "hailomuxer name=hmux "
        pipeline_string += source_element
        pipeline_string += "tee name=t ! "
        pipeline_string += QUEUE("bypass_queue", max_size_buffers=20) + "hmux.sink_0 "
        pipeline_string += "t. ! " + QUEUE("queue_hailonet")
        pipeline_string += "videoconvert n-threads=3 ! "
        pipeline_string += f"hailonet hef-path={self.hef_path} batch-size={self.batch_size} {self.thresholds_str} force-writable=true ! "
        pipeline_string += QUEUE("queue_hailofilter")
        pipeline_string += f"hailofilter so-path={self.default_postprocess_so} qos=false ! "
        pipeline_string += QUEUE("queue_hmuc") + " hmux.sink_1 "
        pipeline_string += "hmux. ! " + QUEUE("queue_hailo_python")
        pipeline_string += QUEUE("queue_user_callback")
        pipeline_string += f"identity name=identity_callback ! "
        pipeline_string += QUEUE("queue_hailooverlay")
        pipeline_string += f"hailooverlay ! "
        pipeline_string += QUEUE("queue_videoconvert")
        pipeline_string += f"videoconvert n-threads=3 qos=false ! "
        pipeline_string += QUEUE("queue_hailo_display")
        pipeline_string += f"fpsdisplaysink video-sink={self.video_sink} name=hailo_display sync={self.sync} text-overlay={self.options_menu.show_fps} signal-fps-measurements=true "
        return pipeline_string

if __name__ == "__main__":
    Users  = []
    Users.append(os.getlogin())
    user   = Users[0]
    h_user = "/home/" + os.getlogin( )
    m_user = "/media/" + os.getlogin( )
    print(h_user,m_user)

    # check if clock synchronised
    if "System clock synchronized: yes" in os.popen("timedatectl").read().split("\n"):
        synced = 1
    else:
        synced = 0
   
    # clear RAM jpegs
    pics = glob.glob('/run/shm/*.jpg')
    pics.sort(reverse = True)
    for x in range(0,len(pics)):
        os.remove(pics[x])
    # initialise variables   
    record  = 0
    b_count = 0  
    f_count = 0 
    start = time.monotonic()
    start2 = time.monotonic()
    startup = time.monotonic()
    now = datetime.datetime.now()
    timestamp = now.strftime("%y%m%d%H%M%S")
    rec_led = LED(led)
    rec_led.off()
    parser = get_default_parser()
    # Add additional arguments here
    parser.add_argument("--network", default="yolov6n", choices=['yolov6n', 'yolov8s', 'yolox_s_leaky'], help="Which Network to use, defult is yolov6n")
    args = parser.parse_args()
    app = GStreamerDetectionApp(args, user_data)
    app.run()
