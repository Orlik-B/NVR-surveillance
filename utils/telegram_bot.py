import io
from datetime import timedelta

import cv2
import numpy as np
from telepot import Bot

from .camera_tools import BufferlessVideoCapture


def send_frame_condition(time_diff, camera_vc, config):
    """
    Check if the time since last notification is greater than set in config and detections occurred X times in a row

    Args:
        time_diff: Time since the last message was sent
        camera_vc: camera videocapture object
        config: config dictionary

    Returns:
    Boolean information if condition has been met
    """
    if (time_diff > timedelta(seconds=int(config['Telegram']['bot_frame_timeout']))
            and camera_vc.detections_in_a_row >= int(config['Parameters']['min_detections_in_a_row'])):
        return True
    else:
        return False


def send_cv2_frame(bot: Bot, frame: np.ndarray, verbose_level: int, config: dict) -> None:
    """
    Send a CV2 frame as a photo using a Telegram bot.

    Args:
        bot: The Telegram bot instance.
        frame: The CV2 frame to be sent.
        verbose_level: Message importance level
        config: Config dictionary

    """
    if int(config['Parameters']['runtime_verbose_level']) >= verbose_level:
        success, encoded_image = cv2.imencode('.jpg', frame)
        if success:
            image_bytes = encoded_image.tobytes()
            image_buffer = io.BytesIO(image_bytes)
            buffered_reader = io.BufferedReader(image_buffer)
            bot.sendPhoto(config['Telegram']['chat_id'], photo=buffered_reader)


def inform_the_user(bot: Bot, information_text: str, verbose_level: int, config: dict):
    """
    Inform the user about <information_text>

    Args:
        bot: bot used to send information
        information_text: content of message
        verbose_level: Message importance level
        config: config dictionary
    """
    if int(config['Parameters']['runtime_verbose_level']) >= verbose_level:
        bot.sendMessage(config['Telegram']['chat_id'], information_text)


def check_and_report_camera_failure(bot: Bot, camera_vc: BufferlessVideoCapture, verbose_level: int, config: dict):
    """
    Report camera failure status after X timeouts

    Args:
        bot: telegram bot object
        camera_vc: camera bufferless videocapture object
        verbose_level: Message importance level
        config: config dictionary
    """
    timeout_count = int(config['Parameters']['timeout_count_before_message'])
    if camera_vc.queue_timeouts_counter == timeout_count and int(config['Parameters']['runtime_verbose_level']) >= verbose_level:
        bot.sendMessage(config['Telegram']['chat_id'], f'camera {camera_vc.name} has failed {timeout_count} times')
