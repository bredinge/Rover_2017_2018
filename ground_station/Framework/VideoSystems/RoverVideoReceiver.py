#####################################
# Imports
#####################################
# Python native imports
from PyQt5 import QtCore, QtGui, QtWidgets
import logging
import cv2
import numpy as np
import qimage2ndarray
import pprint

import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import CompressedImage

# Custom Imports

#####################################
# Global Variables
#####################################
FONT = cv2.FONT_HERSHEY_TRIPLEX


#####################################
# RoverVideoReceiver Class Definition
#####################################
class RoverVideoReceiver(QtCore.QThread):
    publish_message_signal = QtCore.pyqtSignal()
    image_ready_signal = QtCore.pyqtSignal()

    def __init__(self, shared_objects, video_display_label, topic_path):
        super(RoverVideoReceiver, self).__init__()

        # ########## Reference to class init variables ##########
        self.shared_objects = shared_objects
        self.video_display_label = video_display_label  # type:QtWidgets.QLabel
        self.topic_path = topic_path

        # ########## Get the settings instance ##########
        self.settings = QtCore.QSettings()

        # ########## Get the Pick And Plate instance of the logger ##########
        self.logger = logging.getLogger("groundstation")

        # ########## Thread Flags ##########
        self.run_thread_flag = True

        # ########## Class Variables ##########
        # Subscription variables
        # self.video_subscriber = rospy.Subscriber(self.topic_path, CompressedImage,
        #                                          self.__image_data_received_callback)  # type: rospy.Subscriber

        self.subscription_queue_size = 10

        # Steam name variable
        self.video_name = self.topic_path.split("/")[2].replace("_", " ").title()

        # Image variables
        self.raw_image = None
        self.opencv_image = None
        self.pixmap = None

        # Processing variables
        self.bridge = CvBridge()  # OpenCV ROS Video Data Processor
        self.video_enabled = False
        self.new_frame = False

        # Assign local callbacks
        self.__set_local_callbacks()

    def run(self):
        self.logger.debug("Starting \"%s\" Thread")

        while self.run_thread_flag:
            if self.video_enabled:
                self.__show_video_enabled()
            else:
                self.__show_video_disabled()

            self.msleep(18)

        self.logger.debug("Stopping \"%s\" Thread")

    def __show_video_enabled(self):
        if self.new_frame:
            self.opencv_image = self.bridge.compressed_imgmsg_to_cv2(self.raw_image, "rgb8")
            self.opencv_image = cv2.resize(self.opencv_image, (1280, 720))
            self.pixmap = QtGui.QPixmap.fromImage(qimage2ndarray.array2qimage(self.opencv_image))
            self.image_ready_signal.emit()
            self.new_frame = False

    def __show_video_disabled(self):
        if self.new_frame:
            fps_image = np.zeros((720, 1280, 3), np.uint8)

            self.pixmap = QtGui.QPixmap.fromImage(qimage2ndarray.array2qimage(fps_image))
            self.image_ready_signal.emit()
            self.new_frame = False

    def __on_image_update_ready(self):
        self.video_display_label.setPixmap(self.pixmap)

    def __image_data_received_callback(self, raw_image):
        self.raw_image = raw_image
        self.new_frame = True

    def __set_local_callbacks(self):
        self.video_display_label.mouseDoubleClickEvent = self.toggle_video_display

    def toggle_video_display(self, _):
        if self.video_enabled:
            self.video_subscriber.unregister()
            self.new_frame = True
            self.video_enabled = False
        else:
            self.video_subscriber = rospy.Subscriber(self.topic_path, CompressedImage,
                                                     self.__image_data_received_callback)
            self.video_enabled = True

    def connect_signals_and_slots(self):
        self.image_ready_signal.connect(self.__on_image_update_ready)

    def setup_signals(self, start_signal, signals_and_slots_signal, kill_signal):
        start_signal.connect(self.start)
        signals_and_slots_signal.connect(self.connect_signals_and_slots)
        kill_signal.connect(self.on_kill_threads_requested__slot)

    def on_kill_threads_requested__slot(self):
        self.run_thread_flag = False