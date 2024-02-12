import ast
import logging
from datetime import datetime

from ultralytics import YOLO
import cv2
import telepot

from utils.cv_utils import (
    draw_boxes,
    midpoint_bottom,
    is_point_in_rectangle,
    zoom_in_frame,
    draw_metadata,
    show_frame,
    save_detection_frame,
)
from utils.setup_cleanup import load_config, setup_cameras, cleanup_cameras, calculate_frame_size, init_logging
from utils.miscellaneous import calculate_overwatch_end_dt, LoopDelayer, AliveLogger
from utils.telegram_bot import send_cv2_frame, inform_the_user, send_frame_condition, check_and_report_camera_failure


def main():
    # Configuration
    init_logging('logs')  # Start logging to a file
    logging.info('Loading configuration and running initial setup')
    config = load_config()  # Load config file
    bot = telepot.Bot(config['Telegram']['token'])  # Prepare telegram bot for sending messages
    inform_the_user(bot, 'Starting overwatch', 3, config)  # Inform user about overwatch start if verbose is set at level 3 or above

    # Setup
    alive_logger = AliveLogger(config['Parameters']['log_status_every_N_minutes'])
    model = YOLO(config['Model']['path'])  # Load model
    camera_vc_list = setup_cameras(config)  # Initialize camera bufferless videocapture object (as list of objects)
    frame_width, frame_height = calculate_frame_size(camera_vc_list[0], config)  # Calculate desired frame width and height
    loop_iteration_counter = 0
    overwatch_datetime_end = calculate_overwatch_end_dt(config['Parameters']['overwatch_time'])
    loop_delayer = LoopDelayer(config['Parameters']['main_loop_minimum_time_duration'])

    # Main loop of the surveillance process
    logging.info('Starting surveillance process')
    while datetime.now() < overwatch_datetime_end:
        loop_delayer.delay()  # throttle main loop in order to limit CPU/GPU [Power] resources
        alive_logger.log_alive_status()  # Log every N minutes if process is still alive
        loop_iteration_counter += 1

        # For each camera
        for camera_vc in camera_vc_list:
            frame = camera_vc.read()  # Read frame
            if frame is None:
                logging.info(f'Skipping frame at {camera_vc.name} due to videocapture timeout')
                check_and_report_camera_failure(bot, camera_vc, 2, config)
                continue
            frame = zoom_in_frame(frame, config[camera_vc.name]['zoom_in_frame'])  # Zoom in frame if set in config
            frame = cv2.resize(frame, (frame_width, frame_height))  # Resize frame to the model size

            # Put metadata info on a frame (zones, time to overwatch end, num_of_iteration, detections in a row)
            frame = draw_metadata(frame, camera_vc, frame_width, frame_height, overwatch_datetime_end, loop_iteration_counter)

            # Find objects in a frame
            results = model.predict(frame, stream=True, verbose=False, imgsz=int(config['Model']['imgsz']))

            # Process results
            any_detection = False  # Assume that there is no detection of searched objects

            for result in results:
                boxes = result.boxes.cpu().numpy()
                for box in boxes:
                    # if object belongs to one of desired classes and its confidence is above threshold
                    if (box.cls in ast.literal_eval(config['Model']['detection_classes']) and
                            box.conf > float(config['Model']['confidence'])):
                        class_name = result.names[box.cls[0]]
                        coordinates = box.xyxy[0].astype(int)

                        # Check if object is not in 'skip detection zones'. Drop detection if True
                        object_not_in_zones = True  # Assume that object is not in any 'skip zone'
                        for x1, y1, x2, y2 in camera_vc.zones:
                            rectangle_coordinates = (x1 * frame_width, y1 * frame_height, x2 * frame_width, y2 * frame_height)
                            if is_point_in_rectangle(midpoint_bottom(*coordinates), rectangle_coordinates):
                                object_not_in_zones = False
                                break

                        if object_not_in_zones:
                            draw_boxes(frame, box, class_name)
                            any_detection = True

            if any_detection:  # If there is at least one detection on image
                time_diff = datetime.now() - camera_vc.last_detection_dt  # Measure time since last detection
                camera_vc.detections_in_a_row += 1

                # If the time since last notification is greater than set in config
                # and detections occurred X times in a row - send frame with telegram bot
                if send_frame_condition(time_diff, camera_vc, config):
                    logging.info(f'Object has been spotted at camera: {camera_vc.name}')
                    save_detection_frame('logs/detection_frames', frame, camera_vc.name, config['Parameters']['save_frames'])
                    send_cv2_frame(bot, frame, 1, config)  # Inform the user by sending the frame
                    camera_vc.last_detection_dt = datetime.now()  # Reset time since last notification

            # If there are no detections on frame
            else:
                camera_vc.detections_in_a_row = 0  # Zero detections_in_a_row counter

            # Finally, show results in window
            show_frame(frame, config, camera_vc.name)

    # Cleanup part
    logging.info(f'Finishing surveillance')
    inform_the_user(bot, 'Finishing overwatch', 3, config)  # Inform user about overwatch end if verbose is at level 3
    cleanup_cameras(camera_vc_list)  # Release all camera threads before finishing the main process


if __name__ == '__main__':
    main()
