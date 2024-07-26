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

sd_hour = 21

h_user = "/home/" + os.getlogin( )
m_user = "/media/" + os.getlogin( )
print(h_user,m_user)

# check if clock synchronised
synced = 0
os.system("timedatectl >> /run/shm/sync.txt")
# read sync.txt file
try:
    sync = []
    with open("/run/shm/sync.txt", "r") as file:
        line = file.readline()
        while line:
            sync.append(line.strip())
            line = file.readline()
    if sync[4] == "System clock synchronized: yes":
        synced = 1
    else:
        synced = 0
    if trace > 0:
        print("SYNC: ", synced)
except:
    pass

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
    global synced,h_user,m_user,sd_hour,count,record,start,timestamp,pre_frames,user,vid_length,start2,mp4_timer
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
        if (label == "cat" and confidence > 0.35) or (label == "bear" and confidence > 0.35):
            # print(label,confidence)
            # start recording on detection
            if record == 0:
                record = 1
                now = datetime.datetime.now()
                timestamp = now.strftime("%y%m%d%H%M%S")
                start = time.monotonic()
                start2 = time.monotonic()
            else:
                start = time.monotonic()
                start2 = time.monotonic()
    #print(len(detections),record,time.monotonic() - start,time.monotonic() - start2)
    # stop recording if exceeded required length and no detections
    if record == 1 and time.monotonic() - start > vid_length and len(detections) == 0:
        start2 = time.monotonic()
        start  = time.monotonic()
        record = 0
        count  = 0
        # rename jpegs
        pics = glob.glob('/run/shm/frames*.jpg')
        pics.sort(reverse = False)
        frames = 0
        for x in range(0,len(pics)):
            frame2 = "00000" + str(frames)
            os.rename(pics[x],'/run/shm/' + timestamp + "_" + str(frame2[-5:]) + '.jpg')
            frames +=1

    if record == 0: # add to circular buffer
        count +=1
        count2 = "00000" + str(count)
        frame2 = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("/run/shm/frames_" + str(count2[-5:]) + ".jpg",frame2)
        pics = glob.glob('/run/shm/frames*.jpg')
        pics.sort(reverse = True)
        # delete oldest jpeg if > pre_frames set
        jcount = len(pics)
        if jcount > pre_frames:
            os.remove(pics[jcount - 1])
        
    elif record == 1: # record frames
        count +=1
        count2 = "00000" + str(count)
        frame2 = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite("/run/shm/frames_" + str(count2[-5:]) + ".jpg",frame2)
        
    if time.monotonic() - start2 > mp4_timer: # make mp4s if no detections for 10 seconds
        start2 = time.monotonic()
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
                cmd += 'boxcolor=black@0.0:box=1:x=10:y=540" '
                # destination for mp4 output
                cmd += "/home/" + user + "/Videos/" + timestamp + "_1.mp4"
                # run command
                os.system(cmd)
        for y in range(0,len(mpics)):
            os.remove(mpics[y])
        # check if clock synchronised
        if os.path.exists("/run/shm/sync.txt"):
            os.rename('/run/shm/sync.txt', '/run/shm/oldsync.txt')
        os.system("timedatectl >> /run/shm/sync.txt")
        # read sync.txt file
        try:
            sync = []
            with open("/run/shm/sync.txt", "r") as file:
                line = file.readline()
                while line:
                    sync.append(line.strip())
                    line = file.readline()
            if sync[4] == "System clock synchronized: yes":
                synced = 1
            else:
                synced = 0
        except:
            pass
        # check current hour and shutdown
        now = datetime.datetime.now()
        hour = int(now.strftime("%H"))
        # move mp4s to USB if present
        if hour == sd_hour and time.monotonic() - startup > 300 and synced == 1:
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
            source_element = f"libcamerasrc name=src_0 ! " #auto-focus-mode=AfModeManual ! " #auto-focus-mode=2 ! "
            source_element += f"video/x-raw, format={self.network_format}, width=1280, height=1088 ! "
            source_element += QUEUE("queue_src_scale")
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
    user       = Users[0]
    count      = 0
    record     = 0
    pcount     = 0
    vid_length = 3  # seconds
    mp4_timer  = 10
    pre_frames = 60 # frames
    # clear RAM jpegs
    pics = glob.glob('/run/shm/*.jpg')
    pics.sort(reverse = True)
    for x in range(0,len(pics)):
        os.remove(pics[x])
    start = time.monotonic()
    start2 = time.monotonic()
    startup = time.monotonic()
    now = datetime.datetime.now()
    timestamp = now.strftime("%y%m%d%H%M%S")
    parser = get_default_parser()
    # Add additional arguments here
    parser.add_argument("--network", default="yolov6n", choices=['yolov6n', 'yolov8s', 'yolox_s_leaky'], help="Which Network to use, defult is yolov6n")
    args = parser.parse_args()
    app = GStreamerDetectionApp(args, user_data)
    app.run()
