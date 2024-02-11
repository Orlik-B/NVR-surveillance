import threading
import queue
from datetime import datetime
from typing import Union

import cv2
import numpy as np


class BufferlessVideoCapture:
    """
    A class for camera objects capturing video frames without buffering.
    """

    def __init__(self, camera_name: str, rtsp_address: str, zones: list, draw_frames: bool) -> None:
        """
        Initializes the BufferlessVideoCapture object.


        Args:
            camera_name:
            rtsp_address: rtsp address to the camera. For example:
                          rtsp://{USER}:{PASSWORD}@192.168.1.{HOST_PART}:554/{NVR_ADDRESS_TO_CAMERA_STREAM}
            zones: Zones used to skip detections
            draw_frames: Flag for showing window with detection (True can be set only if OS has GUI (is not a server))
        """
        self.cap = cv2.VideoCapture(rtsp_address)
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()
        self._stop = False

        self.name = camera_name
        self.zones = zones
        self.last_detection_dt = datetime(2000, 1, 1, 1, 1, 1)
        self.detections_in_a_row = 0
        self.queue_timeouts_counter = 0
        self.draw_frames = draw_frames

    def __del__(self) -> None:
        """
        Stop the frame read thread and close the video capture.
        """
        self.cap.release()

    def stop_reader(self) -> None:
        """
        Send signal to stop the video capture thread.
        """
        self._stop = True  # Signal the thread to stop

    def _reader(self) -> None:
        """
        Internal method to read video frames asynchronously and store them in the queue.
        """
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)

            # Check if a signal to stop the thread is received
            if self._stop:
                break

    def read(self) -> Union[np.ndarray, None]:
        """
        Retrieves a video frame from the queue.

        Returns:
        The newest video frame.
        """
        try:
            frame = self.q.get(timeout=0.75)
        except queue.Empty:
            self.queue_timeouts_counter += 1
            return None

        return frame
