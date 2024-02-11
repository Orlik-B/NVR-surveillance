import logging
from datetime import datetime, timedelta
import time


def calculate_overwatch_end_dt(overwatch_time: str) -> datetime:
    """
    Calculate the end datetime for an Overwatch session.

    Args:
        overwatch_time: String representing the time for the Overwatch session duration.

    Returns:
    Datetime object representing the calculated end time of the Overwatch session.
    """
    hours, minutes = map(int, overwatch_time.split(':'))
    return datetime.now() + timedelta(hours=hours, minutes=minutes)


def calculate_time_to_end(dt1: datetime, dt2: datetime) -> str:
    """
    Calculate the time difference between two datetime objects and return the result in 'HH:MM:SS' format.

    Args:
        dt1: Datetime object representing the start time.
        dt2: Datetime object representing the end time.

    Returns:
    String representing the time difference in 'HH:MM:SS' format.
    """
    time_difference = dt2 - dt1

    # Convert the time difference to hours, minutes, and seconds
    total_seconds = time_difference.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    # Format the result as 'HH:MM:SS'
    time_difference_formatted = f'{hours:02d}:{minutes:02d}:{seconds:02d}'

    return time_difference_formatted


class LoopDelayer:
    """
    Class used for creating object that main goal is to throttle loop. It is expected to be run at the start
    or at the end of the loop
    Usage: Place: object.delay() at the start of the loop. If minimal_loop_time is set to 2 seconds, it will
           throttle the loop iterations to minimum duration of 2 seconds.
    For example:
        If loop iteration last 1.5 second, object.delay() will sleep for 0.5 second.
        If loop iteration last more than 2 seconds, object.delay() will only do simple pass
    """

    def __init__(self, minimal_loop_time):
        """
        Creates delayer object

        Args:
            minimal_loop_time: Minimum time of the single loop iteration.
        """
        self.minimal_loop_time = float(minimal_loop_time)
        self.previous_delay_time = time.perf_counter()

    def delay(self) -> None:
        """
        Delay loop in order to limit frequency

        """
        time_difference = time.perf_counter() - self.previous_delay_time
        loop_delay_time = self.minimal_loop_time - time_difference

        if loop_delay_time > 0:
            time.sleep(loop_delay_time)
            self.previous_delay_time = time.perf_counter()


class AliveLogger:
    """
    Allows to log every X minutes if script is still running
    """

    def __init__(self, time_interval):
        """
        Initialize AliveLogger object

        Args:
            time_interval: Time interval to log that process is alive
        """
        self.last_log_time = datetime.now()
        self.time_interval = int(time_interval)

    def log_alive_status(self) -> None:
        """
        Log the alive status
        """

        if datetime.now() - self.last_log_time > timedelta(minutes=self.time_interval):
            logging.info('Process is still running')
            self.last_log_time = datetime.now()
