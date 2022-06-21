import asyncio
import datetime
import os
import tkinter as tk
from io import BytesIO

import imageio.v2 as imageio
import numpy as np
import requests
from PIL import Image, ImageDraw
from tqdm import tqdm

from dremel3dpy import _LOGGER, Dremel3DPrinter
from dremel3dpy.helpers.constants import (
    DEFAULT_ADDITIONAL_OUTPUT_SIZE_PERCENTAGE,
    DEFAULT_FINAL_GRACE_PERIOD,
    DEFAULT_INITIAL_PREPARING_PERIOD,
    DEFAULT_MAX_SIZE_MB,
    FRAME_RECTANGLE_MARGIN,
)
from dremel3dpy.helpers.timer import TaskTimer


class Dremel3D45Timelapse:
    def __init__(self, printer: Dremel3DPrinter, loop):
        """"""
        self._printer = printer
        self._should_stop = False
        self._writer = None
        self._video_writer = None
        self._output_file = None
        self._max_output_size = None
        self._printing_progress_bar = None
        self._loop = loop

    def _get_progress_status(self):
        return (
            f"Progress: {self._printer.get_printing_progress()}%",
            f"Elapsed: {self._format_seconds(self._printer.get_elapsed_time())}",
            f"Remaining: {self._format_seconds(self._printer.get_remaining_time())}",
            f"Total: {self._format_seconds(self._printer.get_total_time())}",
        )

    def _get_resource_status(self):
        return (
            f"Model: {self._printer.get_title()}",
            f"Platform: {self._printer.get_temperature_type('platform')}C",
            f"Extruder: {self._printer.get_temperature_type('extruder')}C",
            f"Filament: {self._printer.get_filament()}",
        )

    def _format_seconds(self, seconds):
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        if days > 0:
            return "%dd %dh %dm %ds" % (days, hours, minutes, seconds)
        elif hours > 0:
            return "%dh %dm %ds" % (hours, minutes, seconds)
        elif minutes > 0:
            return "%dm %ds" % (minutes, seconds)
        else:
            return "%ds" % (seconds,)

    def get_snapshot_as_ndarray(self, original, scale):
        snapshot = requests.get("http://192.168.0.60:10123/?action=snapshot")
        bytes_jpgdata = BytesIO(snapshot.content)
        image = Image.open(bytes_jpgdata)
        (w, h) = image.size
        image = image.resize((int(w * scale), int(h * scale)))
        if original:
            return np.asarray(image)

        # Progress Bar
        PROGRESS_BAR_HEIGHT = 5
        origin_x, origin_y = (
            FRAME_RECTANGLE_MARGIN,
            h - FRAME_RECTANGLE_MARGIN - PROGRESS_BAR_HEIGHT,
        )
        rectangle_w = w - origin_x - FRAME_RECTANGLE_MARGIN
        rectangle_h = PROGRESS_BAR_HEIGHT

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)  # Create a context for drawing things on it.
        draw.rectangle(
            [(origin_x, origin_y), (origin_x + rectangle_w, origin_y + rectangle_h)],
            fill=(255, 255, 255, 128),
        )
        draw.rectangle(
            [
                (origin_x, origin_y),
                (
                    origin_x
                    + round(
                        rectangle_w * self._printer.get_printing_progress() / 100.0
                    ),
                    origin_y + rectangle_h,
                ),
            ],
            fill=(0, 127, 0, 128),
        )
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        return np.asarray(image)

    def _append_to_gif(self, writer, original, scale):
        if self._should_continue():
            img = self.get_snapshot_as_ndarray(original, scale)
            if img is not None:
                writer.append_data(img)

    # Add check for printer offline
    def _should_continue(self):
        if not (
            self._loop.is_running()
            and (
                (self._writer is not None and not self._writer.closed)
                or (self._video_writer is not None and self._video_writer.isOpened())
            )
            and not (self._should_stop or self._loop.is_closed())
            and os.path.exists(self._output_file)
        ):
            error_msg = "Due to some resources not being available or opened anymore, we can't continue the media creation. Interrupting..."
            _LOGGER.exception(error_msg)
            raise RuntimeError(error_msg)
        if os.path.getsize(self._output_file) > self._max_output_size * (
            1.0 + DEFAULT_ADDITIONAL_OUTPUT_SIZE_PERCENTAGE
        ):
            output_file_mb = os.path.getsize(self._output_file) / 1024.0 / 1024.0
            max_output_mb = self._max_output_size / 1024.0 / 1024.0
            error_msg = (
                f"The size of your output file reached "
                + "{:.2f}".format(output_file_mb)
                + "MB (Current limit is "
                + "{:.2f}".format(max_output_mb)
                + "MB). Feel free to change that with the flag --max-output-size in megabytes. Interrupting..."
            )
            _LOGGER.exception(error_msg)
            raise RuntimeError(error_msg)

        return True

    def _is_temperature_not_adjusting(self, temp_type, last_temperatures):
        temperature = self._printer.get_temperature_type(temp_type)
        target_temperature = self._printer.get_temperature_attributes(temp_type)[
            "target_temp"
        ]
        not_updating = False
        if not (
            in_range := self._printer.is_maybe_temperature_within_target_range(
                temp_type
            )
        ):
            if (
                target_temperature == 0 and temperature == last_temperatures[temp_type]
            ) or (
                target_temperature != 0
                and (
                    (
                        target_temperature > temperature
                        and temperature <= last_temperatures[temp_type]
                    )
                    or (
                        target_temperature < temperature
                        and temperature >= last_temperatures[temp_type]
                    )
                )
            ):
                not_updating = True
        last_temperatures[temp_type] = temperature
        return (in_range, not_updating)

    def _wait_start_printing(self):
        temps = ["platform", "extruder"]
        last_temps = {key: 0 for key in temps}
        self._total_temp_errors = 0

        initial_printing_state_busy = (
            self._printer.is_busy() and not self._printer.is_completed()
        )

        def _inner_wait_start_printing():
            self._printer.set_job_status(refresh=True)

            # Printer is not busy anymore, therefore we should quit waiting for the temperature warmup.
            new_printing_state_busy = (
                self._printer.is_busy() and not self._printer.is_completed()
            )
            if initial_printing_state_busy and not new_printing_state_busy:
                error_msg = "The printer unexpectedly became no longer busy or has completed the printing job."
                _LOGGER.warning(error_msg)
                return False

            if self._printer.is_building():
                # Here we stop waiting because we reached a point where the printer
                # phase is back on building and the API returned a positive number
                # for the expected total time for the job to complete. Without that
                # our lives becomes much harder measuring the resources.
                return False
            elif self._printer.is_printing():
                # Here we keep on waiting because although the printer is not on the
                # building phase, it's on the printing phase. Printing phase is anything
                # that is not "completed" or "ready". So we would continue waiting here
                # if the printer phase was either "pausing", "paused", "resuming" or
                # "preparing", but not "building" (yet).
                return True

            # Lets check how many times we verified the temperature adjustments and it
            # failed our checks.
            temp_errors = list(
                map(
                    lambda temp_type: (
                        self._is_temperature_not_adjusting(temp_type, last_temps)
                    ),
                    temps,
                )
            )
            # TODO(stor): Fix this check. If the printer is not building, not paused, or, in other words,
            # on the way from a non-printing status to a printing status, then we should check two things:
            # 1. The target temperature is non-zero, at least after a few calls to the API, we will always
            #    eventually have a value.
            # 2. The temperatures are moving towards the target. If the target is lower, the temperatures
            #    are decreasing with time. If they are higher, they are increasing. They can't be stuck
            #    with the same value for so long, unless they reached the target temperature.
            in_range_1, not_updating_1 = temp_errors[0]
            in_range_2, not_updating_2 = temp_errors[1]
            if (
                (not in_range_1 or not in_range_2)
                and (in_range_1 or not_updating_1)
                and (in_range_2 or not_updating_2)
            ):
                self._total_temp_errors += 1
            else:
                self._total_temp_errors = 0

            # We verified for 10 minutes straight that the temperatures
            # were not adjusting, therefore we should quit.
            if self._total_temp_errors > 60 * 10:
                error_msg = "Platform or Extruder temperatures does not seem to be moving for the last 10 minutes. Interrupting..."
                _LOGGER.exception(error_msg)
                raise RuntimeError(error_msg)
            return True

        return _inner_wait_start_printing

    def _update_printing_progress_bar(self, silent):
        if self._printing_progress_bar is not None:
            if silent and self._printing_progress_bar.disable:
                return self._printing_progress_bar
            elif silent and not self._printing_progress_bar.disable:
                self._printing_progress_bar.close()
                return self._printing_progress_bar
            elif not silent and not self._printing_progress_bar.disable:
                return self._printing_progress_bar
            else:
                # Last case is that it's not silent and progress_bar is disabled.
                self._printing_progress_bar.close()
        self._printer.set_job_status(refresh=True)
        self._printing_progress_bar = tqdm(
            desc="Printing Progress",
            initial=self._printer.get_printing_progress(),
            total=100.0,
            colour="green",
            position=0,
            leave=True,
            unit="%",
            disable=silent,
        )
        self._printing_progress_bar.refresh()
        return self._printing_progress_bar

    async def wait_target_temperatures(self, silent):
        if not self._printer.is_busy():
            error_msg = "When getting ready to warmup the printer, the job got cancelled. Interrupting..."
            _LOGGER.exception(error_msg)
            raise RuntimeError(error_msg)

        if self._printer.is_building():
            _LOGGER.info(
                "The temperature sensors got to their target level and the printer is ready to start building."
            )
            return False

        if self._printer.is_aborted():
            error_msg = "Printing job was aborted. Interrupting..."
            _LOGGER.exception(error_msg)
            raise RuntimeError(error_msg)

        # While the printer is paused, we keep running this loop until is changes phase.
        if self._printer.is_paused() or self._printer.is_pausing():
            return True

        # We patched this function and now should work properly. So, if the job is completed,
        # exit this job.
        if self._printer.is_completed():
            return False

        # After all the check aboves, the only phases the printer can be are:
        # - Idle
        # - Building
        # - Preparing
        # - Resuming

        printing_progress_bar = self._update_printing_progress_bar(True)
        printing_progress_bar.close()

        # We close the printing progress bar to restart the temperature progress bars.
        _LOGGER.info("Waiting on temperatures to rise to their target levels.")
        temperature_progress = {
            temp_type: tqdm(
                desc=f"{temp_type.capitalize()} Temperature",
                initial=self._printer.get_temperature_type(temp_type),
                total=None,
                colour="blue",
                leave=False,
                unit="°C",
                bar_format="{desc}: {n_fmt}°C [{elapsed}]\b\b",
                disable=silent,
            )
            for temp_type in ["platform", "extruder"]
        }

        def update_temperature_progress():
            self._printer.set_job_status(refresh=True)
            for i, temp_type in enumerate(temperature_progress.keys()):
                target_temp = self._printer.get_temperature_attributes(temp_type)[
                    "target_temp"
                ]
                progress_bar = temperature_progress[temp_type]
                progress_bar.position = i
                if target_temp != 0:
                    progress_bar.n = 0
                    progress_bar.total = target_temp
                    progress_bar.bar_format = "{l_bar}{bar}{r_bar}\b\b"
                progress_bar.update(
                    self._printer.get_temperature_type(temp_type) - progress_bar.n
                )
                progress_bar.refresh()

        wait_start_printing = self._wait_start_printing()

        async def keep_waiting_condition():
            return self._should_continue() and wait_start_printing()

        timer = TaskTimer(
            continue_condition=keep_waiting_condition,
            refresh_fn=update_temperature_progress,
            sleep_interval=1,
            loop=self._loop,
        )
        await timer.start()
        [progress.close() for _, progress in temperature_progress.items()]

        if not self._printer.is_busy():
            error_msg = "The job got abruptly cancelled. Interrupting..."
            _LOGGER.exception(error_msg)
            raise RuntimeError(error_msg)

        _LOGGER.info(
            f"Platform temperature reached the target of {self._printer.get_temperature_type('platform')}°C"
        )
        _LOGGER.info(
            f"Extruder temperature reached the target of {self._printer.get_temperature_type('extruder')}°C"
        )
        return False

    async def gen_media_file(
        self,
        output,
        fps,
        duration,
        length,
        idle,
        silent,
        file_append_fn,
    ):
        start = datetime.datetime.now()
        has_graceful_exit = not idle and duration
        global snapshot_interval
        snapshot_interval = 1.0

        try:
            if not idle:
                # Initial wait while the machine has probably started a printing job
                # but its status hasn't been updated to busy.
                if not (
                    self._printer.is_busy() and self._printer.get_remaining_time() > 0
                ):
                    _LOGGER.info(
                        "Gracefully waiting for at most 20 minutes for the printer to start."
                    )

                    start_progress = tqdm(
                        desc="Waiting for the printer to start a new print job...",
                        initial=0,
                        total=None,
                        unit_scale=1,
                        colour="white",
                        position=0,
                        leave=False,
                        bar_format="{desc}: {elapsed}\b\b",
                        disable=silent,
                    )

                    async def keep_waiting_get_busy_condition():
                        return self._should_continue() and not (
                            self._printer.is_busy()
                            and self._printer.get_remaining_time() > 0
                        )

                    def start_refresh_fn():
                        self._printer.set_job_status(refresh=True)
                        start_progress.update()

                    timer = TaskTimer(
                        continue_condition=keep_waiting_get_busy_condition,
                        refresh_fn=start_refresh_fn,
                        sleep_interval=1,
                        total_time=DEFAULT_INITIAL_PREPARING_PERIOD,
                        loop=self._loop,
                    )
                    await timer.start()
                    start_progress.close()
                    _LOGGER.info(
                        "Printer is ready to start heating its platform and extruder and starts building."
                    )

                if duration:
                    snapshot_interval = (self._printer.get_remaining_time() + 0.0) / (
                        duration * fps
                    )
                elif length:
                    snapshot_interval = 1.0 / fps
                else:
                    error_msg = "This error is unlikely to happen. When not in --idle mode, even if you don't define the number of seconds in the output media by definining --duration nor --length, we'll calculate it automatically for you using the flag --max-output-size which will always have a default value."
                    _LOGGER.exception(error_msg)
                    raise RuntimeError(error_msg)

                await self.wait_target_temperatures(silent)
            else:
                snapshot_interval = 1.0 / fps

            _LOGGER.info(
                "The printer adjusted the temperatures and its ready to start printing."
            )
            _LOGGER.info(f"A snapshot will be taken every {snapshot_interval} seconds.")

            async def keep_recording_condition():
                self._printer.set_job_status(refresh=True)
                if self._should_continue():
                    if idle:
                        return True
                    if (
                        not self._printer.is_busy()
                        or self._printer.is_completed()
                        or not self._printer.is_printing()
                    ):
                        _LOGGER.info(f"Your printer has completed printing.")
                        return False
                    if self._printer.is_paused() or self._printer.is_pausing():
                        return True
                    if self._printer.is_building():
                        return True
                    return not await self.wait_target_temperatures(silent)
                return False

            def refresh_recording_fn():
                self._printer.set_job_status(refresh=True)
                if not idle:
                    printing_progress_bar = self._update_printing_progress_bar(silent)
                    printing_progress_bar.update(
                        self._printer.get_printing_progress() - printing_progress_bar.n
                    )
                    printing_progress_bar.refresh()
                file_append_fn()

            timer = TaskTimer(
                continue_condition=keep_recording_condition,
                refresh_fn=refresh_recording_fn,
                snapshot_interval=snapshot_interval,
                total_time=(length and length - 1) or None,
                loop=self._loop,
            )
            await timer.start()
            printing_progress = self._update_printing_progress_bar(silent)
            printing_progress.close()

            # We just add this graceful exit period for the --duration arg.
            if has_graceful_exit:
                _LOGGER.info(
                    "Now that the printer finished building, your setup requires a few additional grace seconds to be added to the media so it shows clean pictures without the extrudor motor in front of it."
                )

                completing_progress = tqdm(
                    desc="Finishing...",
                    initial=0,
                    total=fps,
                    unit_scale=1,
                    colour="white",
                    position=0,
                    leave=False,
                    disable=silent,
                )

                async def keep_completing_condition():
                    return self._should_continue() and (
                        self._printer.is_building()
                        or self._printer.is_completed()
                        or self._printer.is_ready()
                    )

                def refresh_completing_fn():
                    self._printer.set_job_status(refresh=True)
                    completing_progress.update(1)
                    file_append_fn()
                    _LOGGER.info(self._printer.get_printing_status())

                timer = TaskTimer(
                    continue_condition=keep_completing_condition,
                    refresh_fn=refresh_completing_fn,
                    snapshot_interval=(DEFAULT_FINAL_GRACE_PERIOD + 0.0) / fps,
                    total_time=DEFAULT_FINAL_GRACE_PERIOD,
                    loop=self._loop,
                )
                await timer.start()
                completing_progress.close()
                _LOGGER.info("All done, feel free to enjoy your output gif or video!")

            end = datetime.datetime.now()
            _LOGGER.info(f"Total timelapse creation time: {end - start}.")
            _LOGGER.info(
                f"Total output file size: "
                + "{:.2f}".format(os.path.getsize(output) / 1024.0 / 1024.0)
                + "MB"
            )
        except asyncio.exceptions.CancelledError as exc:
            raise exc
        except RuntimeError as exc:
            raise exc
        except Exception as exc:
            raise exc
        finally:
            _LOGGER.info("Recording completed. Releasing resources.")
            self.stop_timelapse()

    def _start_media_record(
        self, output_path, fps, duration, length, write_and_close_fn
    ):
        filepath, filename = os.path.split(output_path)
        _, extension = os.path.splitext(output_path)
        _LOGGER.info(
            f"Creating a temporary {extension} file to hold 1 single frame of the video capture in order to measure the expected size in bytes by frame."
        )
        hidden_temp_file = os.path.join(filepath, f".{filename}")
        write_and_close_fn(hidden_temp_file)
        bytes_per_frame = bytes_per_frame = os.path.getsize(hidden_temp_file)
        os.remove(hidden_temp_file)
        _LOGGER.info(
            f"We estimate that each frame saved to your media will increase the final file size by "
            + "{:.2f}".format(bytes_per_frame / 1024.0)
            + "KB."
        )
        max_output_bytes = self._max_output_size
        max_total_frames = max_output_bytes / bytes_per_frame
        if duration:
            # If duration is set, we might need to change the fps
            # in order to not extrapolate the maximum output size.
            if max(1, round(max_total_frames / duration)) < fps:
                old_fps = fps
                fps = max(1, round(max_total_frames / duration))
                _LOGGER.warning(
                    "We needed to make a few adjustments to your media settings to respect your resource limits."
                )
                _LOGGER.warning(
                    f"The --max-output-size flag (with a default value of {DEFAULT_MAX_SIZE_MB}MB) is "
                    + "{:.2f}".format(max_output_bytes / 1024.0 / 1024.0)
                    + "MB."
                )
                _LOGGER.warning(
                    f"In order for the final media file does not extrapolate that size, it can have at most {round(max_total_frames)} frames saved to it."
                )
                _LOGGER.warning(
                    f"Since you defined an output media that will cover the entire printing job timelapse in {duration}s, we wanted to respect that. Therefore, the number of frames/second needed to be reduced from {old_fps} to {fps}."
                )
        elif length:
            # If length is set, the timelapse of the media won't
            # go through all of the painting job, for only for
            # the first length seconds. Let's apply the same logic
            # here to maybe recalculate the fps based on the max
            # output size.
            if max(1, round(max_total_frames / length)) < fps:
                old_fps = fps
                fps = max(1, round(max_total_frames / duration))
                _LOGGER.warning(
                    "We needed to make a few adjustments to your media settings to respect your resource limits."
                )
                _LOGGER.warning(
                    f"The --max-output-size flag (with a default value of {DEFAULT_MAX_SIZE_MB}MB) is "
                    + "{:.2f}".format(max_output_bytes / 1024.0 / 1024.0)
                    + "MB."
                )
                _LOGGER.warning(
                    f"In order for the final media file does not extrapolate that size, it can have at most {round(max_total_frames)} frames saved to it."
                )
                _LOGGER.warning(
                    f"Since you defined an output media final that will record {length}s of the printing job, we wanted to respect that. Therefore, the number of frames/second needed to be reduced from {old_fps} to {fps}."
                )
        else:
            # If duration or length are not set, we keep fps as it is, but we
            # prioritize defining a timelapse duration, and not a fixed length,
            # that will keep the file size not extrapolate maximum output size.
            duration = max_total_frames / fps
            _LOGGER.warning(
                f"You did not specify a duration nor a length of how many seconds your final media file will have (either a fast timelapse for the case of --duration or the exact number of seconds for the case of --length). Therefore, in order to keep the output file size within "
                + "{:.2f}".format(max_output_bytes / 1024.0 / 1024.0)
                + "MB, we defined that the output media file will have approximately "
                + "{:.1f}".format(duration)
                + " seconds."
            )
        assert duration is not None or length is not None
        return fps, duration, length

    async def start_timelapse(
        self,
        output_path,
        fps,
        max_output_size,
        duration,
        length,
        idle,
        original,
        scale,
        silent,
    ):
        _LOGGER.info(f"Building a timelapse gif to {output_path}.")
        if os.path.exists(output_path):
            os.remove(output_path)
        self._writer = imageio.get_writer(output_path, mode="I", fps=fps, format="GIF")
        self._output_file = output_path
        self._max_output_size = max_output_size * 1024.0 * 1024.0
        self._should_stop = False

        def write_and_close_fn(temp_file):
            temp_writer = imageio.get_writer(temp_file, mode="I", fps=fps, format="GIF")
            self._append_to_gif(temp_writer, original, scale)
            temp_writer.close()

        fps, duration, length = self._start_media_record(
            output_path, fps, duration, length, write_and_close_fn
        )

        await self.gen_media_file(
            output_path,
            fps,
            duration,
            length,
            idle,
            silent,
            lambda: self._append_to_gif(self._writer, original, scale),
        )

    def _get_scaled_dimensions(self, scale):
        frame = self.get_snapshot_as_ndarray(True, scale)
        if frame is None:
            return (0, 0)
        return frame.shape[:2]

    def _play_video(self, lbVideo, original, scale):
        self._printer.set_job_status(refresh=True)
        original_canvas = original and self._printer.is_running()
        snapshot = self.get_snapshot_as_ndarray(original_canvas, scale)
        # cv2image = cv2.cvtColor(snapshot, cv2.COLOR_BGR2RGBA)
        # fromarray = Image.fromarray(cv2image)
        # imgtk = ImageTk.PhotoImage(image=fromarray)
        # lbVideo.imgtk = imgtk
        # lbVideo.configure(image=imgtk)

    async def start_stream(self, original, scale):
        try:
            window = tk.Tk(className="3D45 Stream")
            window.resizable(width=False, height=False)
            (h, w) = self._get_scaled_dimensions(scale)
            window.geometry(f"{w}x{h}")
            window.config(highlightbackground="#000000")
            lbVideo = tk.Label(window, bg="white")
            lbVideo.pack()
            while True:
                self._play_video(lbVideo, original, scale)
                window.update()
                await asyncio.sleep(0.01)
        except Exception as exc:
            pass

    def stop_timelapse(self):
        self._should_stop = True
        if self._writer is not None and not self._writer.closed:
            self._writer.close()
        if self._video_writer is not None and self._video_writer.isOpened():
            self._video_writer.release()
