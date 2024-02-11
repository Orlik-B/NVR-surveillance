import ast
import configparser
import datetime
import os.path
import sys
import time
import logging

import cv2

from utils.camera_tools import BufferlessVideoCapture


def unhandled_excepthook(exc_type, exc_value, exc_traceback):
    """
    Exception hook to catch traceback errors into a log file
    """
    logging.error('UNHANDLED PYTHON ERROR: ', exc_info=(exc_type, exc_value, exc_traceback))


def init_logging(path_to_log_folder: str):
    """
    Set up logging into a log file.
    Catch errors (Python tracebacks included) into a log file.

    Args:
        path_to_log_folder: path to logs folder

    """
    start_datetime = datetime.datetime.now().strftime('%Y_%m_%d___%H_%M_%S')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.FileHandler(os.path.join(path_to_log_folder, f'run_{start_datetime}.log')), console_handler],
    )

    sys.excepthook = unhandled_excepthook


def load_config(path_to_config: str = './config.ini') -> configparser.ConfigParser:
    """
    Load configuration settings from an INI file.

    Args:
        path_to_config: String representing the path to the configuration INI file (default is './config.ini').

    Returns:
    ConfigParser object containing the loaded configuration settings.
    """
    config = configparser.ConfigParser()
    config.read(path_to_config)

    return config


def setup_cameras(config: configparser.ConfigParser) -> list[BufferlessVideoCapture]:
    """
    Set up cameras based on the configuration settings.

    Args:
        config: ConfigParser object containing the configuration settings.

    Returns:
    Dictionary containing camera bufferless videocapture objects.
    """
    camera_config_section_names = [x for x in config.sections() if x[:7] == 'Camera_']
    camera_vc_list = []

    for camera_config in camera_config_section_names:
        base_address = config['Parameters']['base_address'].replace('{channel}', config[camera_config]['camera_channel'])
        zones = ast.literal_eval(config[camera_config]['zones'])
        draw_frames = eval(config[camera_config]['show_camera_window'])
        if not isinstance(draw_frames, bool):
            raise ValueError("'show_camera_window' should be set to 'True' or 'False'")

        camera_vc = BufferlessVideoCapture(camera_config, base_address, zones, draw_frames)
        camera_vc_list.append(camera_vc)

    return camera_vc_list


def cleanup_cameras(cameras_list: list[BufferlessVideoCapture]):
    """
    Initialize all videocapture threads shutdown.
    Wait a while to make sure that all threads will be shutdown until end of main program.

    Args:
        cameras_list: list with bufferless videocapture objects
    """
    for camera_vc in cameras_list:
        camera_vc.stop_reader()  # Initialize thread stop

    time.sleep(1)  # Wait a sec for all threads to release
    cv2.destroyAllWindows()  # Destroy windows if they are visible


def calculate_frame_size(camera_vc: BufferlessVideoCapture, config: dict):
    """
    Calculate frame width and height of desired frame shape

    Args:
        camera_vc: camera bufferless videocapture object
        config: config dictionary

    Returns:
        calculated width and height

    """
    frame = camera_vc.read()
    width = int(config['Model']['imgsz'])
    height = int(frame.shape[0] * int(config['Model']['imgsz']) / frame.shape[1])
    return width, height
