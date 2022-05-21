import asyncio
import datetime
import glob
import io
import os
import time

import cv2
import imageio.v2 as imageio
import imageio.v2 as imutils
import numpy as np

from dremel3dpy import _LOGGER, Dremel3DPrinter
from dremel3dpy.helpers.constants import (
    GIF_COMPLETED_GRACE_PERIOD,
    GIF_DEFAULT_FPS,
    GIF_DEFAULT_FRAMES,
    GIF_ENCODE_PARAM,
    GIF_POLLING_INTERVAL_UNTIL_START,
    GIF_UPDATE_JOB_STATUS_INTERVAL,
)


class Dremel3D45Timelapse:
    def __init__(self, printer: Dremel3DPrinter):
        """"""
        self._printer = printer

    def _append_to_gif(self, writer, cap):
        ret, frame = cap.read()
        if ret and np.size(frame) > 0:
            frame = cv2.resize(frame, (500, 500))
            image_bytes = cv2.imencode(".jpg", frame, GIF_ENCODE_PARAM)[1].tobytes()
            buffer = io.BytesIO(image_bytes)
            image = imageio.imread(buffer)
            writer.append_data(image)

    async def start_timelapse(
        self,
        gif_path,
        gif_fps=GIF_DEFAULT_FPS,
        gif_total_frames=GIF_DEFAULT_FRAMES,
    ):
        await asyncio.sleep(5)
        self._printer.set_job_status(refresh=True)
        if not self._printer.is_busy():
            raise RuntimeError(
                "Printer must be printing a job in order to generate a timelapse gif"
            )
        self._should_stop = False
        cap = cv2.VideoCapture(self._printer.get_stream_url())
        if os.path.exists(gif_path):
            os.remove(gif_path)

        while (
            not self._should_stop
            and self._printer.is_busy()
            and not self._printer.is_building()
        ):
            self._printer.set_job_status(refresh=True)
            await asyncio.sleep(GIF_POLLING_INTERVAL_UNTIL_START)

        self._printer.set_job_status(refresh=True)
        total_time = max(
            self._printer.get_total_time(), self._printer.get_remaining_time()
        )
        if total_time == 0:
            # Default total time if we are not able to grab it from the API
            # is 1 hour.
            total_time = 60 * 60
            _LOGGER.warning(
                "Couldn't fetch total time from the printing job, using 1 hour as default"
            )

        sleep_interval = total_time / gif_total_frames
        with imageio.get_writer(gif_path, mode="I", fps=gif_fps) as writer:
            next_refresh_job_status_time = datetime.datetime.now() + datetime.timedelta(
                seconds=GIF_UPDATE_JOB_STATUS_INTERVAL
            )
            while (
                cap.isOpened()
                and not self._should_stop
                and self._printer.is_busy()
                and self._printer.is_building()
            ):
                if (now := datetime.datetime.now()) >= next_refresh_job_status_time:
                    self._printer.set_job_status(refresh=True)
                    next_refresh_job_status_time = now + datetime.timedelta(
                        seconds=GIF_UPDATE_JOB_STATUS_INTERVAL
                    )

                # Skip appending to the gif while the printer is printing but not building
                # (i.e, paused, pausing, resuming or preparing).
                if self._printer.is_building():
                    self._append_to_gif(writer, cap)
                await asyncio.sleep(sleep_interval)
            self._printer.set_job_status(refresh=True)
            now = datetime.datetime.now()
            while (
                cap.isOpened()
                and not self._should_stop
                and datetime.datetime.now()
                < now + datetime.timedelta(seconds=GIF_COMPLETED_GRACE_PERIOD)
            ):
                if self._printer.is_completed():
                    self._append_to_gif(writer, cap)
                await asyncio.sleep(max(1 / gif_fps, 0.1))
            cap.release()
            writer.close()
            cv2.destroyAllWindows()

    def stop_timelapse(self):
        self._should_stop = True
