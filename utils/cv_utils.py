import ast
import os.path
from datetime import datetime
from typing import Tuple

import cv2
import numpy as np
from ultralytics.engine.results import Boxes

from .miscellaneous import calculate_time_to_end
from .camera_tools import BufferlessVideoCapture


def draw_boxes(frame: np.ndarray, box: Boxes, class_name: str) -> None:
    """
    Draw bounding boxes and information on the given frame.

    Args:
        frame: The input image frame.
        box: Object containing detection data.
        class_name: The class name of the object.
    """
    coordinates = box.xyxy[0].astype(int)

    # Draw bounding box on the image
    cv2.rectangle(frame, tuple(coordinates[:2]), tuple(coordinates[2:]), (0, 0, 255), 2)

    # Draw confidence score
    cv2.putText(frame, str(round(box.conf[0], 2)), tuple(coordinates[:2]), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Draw class name
    cv2.putText(frame, class_name, (coordinates[0], coordinates[3]), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)


def midpoint_bottom(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """
    Calculate the midpoint at the bottom of rectangle.

    Args:
        x1: X-coordinate of the first point.
        y1: Y-coordinate of the first point.
        x2: X-coordinate of the second point.
        y2: Y-coordinate of the second point.

    Returns:
    Tuple containing the X and Y coordinates of the midpoint at the bottom.
    """
    return (x1 + x2) / 2, max(y1, y2)


def midpoint(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """
    Calculate the midpoint of a rectangle.

    Args:
        x1: X-coordinate of the first point.
        y1: Y-coordinate of the first point.
        x2: X-coordinate of the second point.
        y2: Y-coordinate of the second point.

    Returns:
    Tuple containing the X and Y coordinates of the midpoint.
    """
    return (x1 + x2) / 2, (y1 + y2) / 2


def is_point_in_rectangle(point: Tuple[float, float], rectangle: Tuple[float, float, float, float]) -> bool:
    """
    Check if a given point is within a specified rectangle.

    Args:
        point: Tuple containing the X and Y coordinates of the point.
        rectangle: Tuple containing the X1, Y1 (top-left corner) and X2, Y2 (bottom-right corner) coordinates of the rectangle.

    Returns:
    True if the point is inside the rectangle, False otherwise.
    """
    x1, y1, x2, y2 = rectangle
    x, y = point
    return x1 < x < x2 and y1 < y < y2


def zoom_in_frame(frame: np.ndarray, zoom_in_params: str) -> np.ndarray:
    """
    Zoom in frame to the coordinates given in camera config section

    Args:
        frame: NumPy array representing the input image frame.
        zoom_in_params: String representation of a list containing four values [left, right, top, bottom] to zoom in the frame.

    Returns:
    NumPy array representing zoomed in frame.
    If the strip_params are not valid, the original frame is returned.
    """
    zoom_in_params_literal = ast.literal_eval(zoom_in_params)
    if isinstance(zoom_in_params_literal, list) and len(zoom_in_params_literal) == 4:
        left, right, top, bottom = zoom_in_params_literal
        new_height = frame.shape[0] - (top + bottom)
        new_width = frame.shape[1] - (left + right)
        return frame[top : top + new_height, left : left + new_width]
    else:
        return frame


def draw_filled_rectangle_with_alpha(image: np.ndarray,
                                     pt1: Tuple[int, int],
                                     pt2: Tuple[int, int],
                                     color: Tuple[int, int, int],
                                     alpha: float = 0.5) -> np.ndarray:
    """
    Draw a filled rectangle on the input image with alpha transparency.

    Args:
        image: NumPy array representing the input image.
        pt1: Tuple containing (x, y) coordinates of one corner of the rectangle.
        pt2: Tuple containing (x, y) coordinates of the opposite corner of the rectangle.
        color: Tuple containing (B, G, R) values for the rectangle color.
        alpha: Alpha value for blending (default is 0.5).

    Returns:
    Numpy array representing the image with the filled rectangle.
    """
    overlay = image.copy()
    cv2.rectangle(overlay, pt1, pt2, color, -1)  # Draw the filled rectangle on the overlay

    # Combine the overlay with the original image using alpha blending
    cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

    return image


def draw_metadata(
    frame: np.ndarray,
    camera: BufferlessVideoCapture,
    frame_width: int,
    frame_height: int,
    overwatch_datetime_end: datetime,
    loop_iteration_counter: int,
):
    """
    Draw:
        - restricted zones
        - processed frames counter
        - detections in a row
        - time to end of surveillance
    Args:
        frame: processed frame
        camera: camera and metadata dictionary
        frame_width:
        frame_height:
        overwatch_datetime_end:
        loop_iteration_counter: processed frames counter

    Returns:
    Frame with metadata
    """
    for x1, y1, x2, y2 in camera.zones:
        frame = draw_filled_rectangle_with_alpha(
            frame,
            (int(x1 * frame_width), int(y1 * frame_height)),
            (int(x2 * frame_width), int(y2 * frame_height)),
            (32, 148, 229),
            0.5,
        )
    cv2.putText(frame, calculate_time_to_end(datetime.now(), overwatch_datetime_end), (1, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    cv2.putText(frame, str(loop_iteration_counter), (1, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.putText(frame, str(camera.detections_in_a_row), (1, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    return frame


def show_frame(frame, config, camera_key):
    """
    Show frame in a window

    Args:
        frame: frame that will be displayed
        config: config dictionary
        camera_key: camera name used to name the window
    """
    if config[camera_key]['show_camera_window'] == 'True':
        cv2.imshow(f'{camera_key}', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            pass


def save_detection_frame(path, frame, camera_name, save):
    """
    Save frame with detection to a specified directory

    Args:
        path: path to save directory
        frame: frame to be saved
        camera_name: camera name as str
        save: boolean flag to proceed save
    """
    if eval(save):
        detection_datetime = datetime.now().strftime('%Y_%m_%d___%H_%M_%S')
        cv2.imwrite(os.path.join(path, f'{detection_datetime}_{camera_name}.jpg'), frame)
