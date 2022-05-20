#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
dremel3dpy by Gustavo Stor - A Dremel 3D Printer Python library.

https://github.com/godely/dremel3dpy

Published under the MIT license - See LICENSE file for more details.

This library supports the three Dremel models: 3D20, 3D40 and 3D45.

"Dremel" is a trademark owned by Dremel, see www.dremel.com for
more information. I am in no way affiliated with Dremel.
"""

import json
import logging
import os
import random
import re
import string
from typing import Any

import requests
import validators
from urllib3.exceptions import InsecureRequestWarning
from yarl import URL

from dremel3dpy.helpers.constants import (
    AVAILABLE_STORAGE,
    CAMERA_PORT,
    CANCEL_COMMAND,
    CHAMBER_TEMPERATURE,
    COMMAND_PATH,
    COMMAND_PORT,
    CONF_API_VERSION,
    CONF_CONNECTION_TYPE,
    CONF_ETHERNET_CONNECTED,
    CONF_ETHERNET_IP,
    CONF_FIRMWARE_VERSION,
    CONF_HOST,
    CONF_MACHINE_TYPE,
    CONF_MODEL,
    CONF_SERIAL_NUMBER,
    CONF_TITLE,
    CONF_WIFI_CONNECTED,
    CONF_WIFI_IP,
    DOOR_OPEN,
    DREMEL_MANUFACTURER,
    ELAPSED_TIME,
    ERROR_CODE,
    ESTIMATED_TOTAL_TIME,
    EXTRA_STATUS_PORT,
    EXTRUDER_TARGET_TEMPERATURE,
    EXTRUDER_TEMPERATURE,
    EXTRUDER_TEMPERATURE_RANGE,
    FAN_SPEED,
    FILAMENT,
    HOME_MESSAGE_PATH,
    JOB_NAME,
    JOB_STATUS,
    NETWORK_BUILD,
    PAUSE_COMMAND,
    PLATFORM_TARGET_TEMPERATURE,
    PLATFORM_TEMPERATURE,
    PLATFORM_TEMPERATURE_RANGE,
    PRINT_COMMAND,
    PRINT_FILE_UPLOADS,
    PRINTER_INFO_COMMAND,
    PRINTER_STATUS_COMMAND,
    PROGRESS,
    REMAINING_TIME,
    REQUEST_TIMEOUT,
    RESUME_COMMAND,
    STATS_FILAMENT_USED,
    STATS_FILE_NAME,
    STATS_INFILL_SPARSE_DENSITY,
    STATS_LAYER_HEIGHT,
    STATS_SOFTWARE,
    STATUS,
    USAGE_COUNTER,
)

_LOGGER = logging.getLogger(__name__)


class Dremel3DPrinter:
    """Main Dremel 3D Printer class."""

    def __init__(self, host: str) -> None:
        """Init a Dremel 3D Printer instance"""
        self._host = host
        self._printer_info = None
        self._job_status = None
        self._printer_extra_stats = None
        self.refresh()

    def set_printer_info(self, refresh=False):
        """Return attributes related to the printer."""
        if refresh or self._printer_info is None:
            try:
                printer_info = default_request(self._host, PRINTER_INFO_COMMAND)
            except RuntimeError as exc:
                _LOGGER.exception(str(exc))
                self._printer_info = None
            else:
                title = re.search(
                    r"DREMEL [^\s+]+", printer_info[CONF_MACHINE_TYPE]
                ).group(0)
                model = re.search(
                    r"DREMEL ([^\s+]+)", printer_info[CONF_MACHINE_TYPE]
                ).group(1)
                self._printer_info = {
                    CONF_HOST: self._host,
                    CONF_API_VERSION: printer_info[CONF_API_VERSION],
                    CONF_CONNECTION_TYPE: "eth0"
                    if printer_info[CONF_ETHERNET_CONNECTED] == 1
                    else "wlan",
                    CONF_ETHERNET_IP: printer_info[CONF_ETHERNET_IP]
                    if printer_info[CONF_ETHERNET_CONNECTED] == 1
                    else "n-a",
                    CONF_FIRMWARE_VERSION: printer_info[CONF_FIRMWARE_VERSION],
                    CONF_MACHINE_TYPE: printer_info[CONF_MACHINE_TYPE],
                    CONF_MODEL: model,
                    CONF_SERIAL_NUMBER: printer_info[CONF_SERIAL_NUMBER],
                    CONF_TITLE: title,
                    CONF_WIFI_IP: printer_info[CONF_WIFI_IP]
                    if printer_info[CONF_WIFI_CONNECTED] == 1
                    else "n-a",
                }

    def set_job_status(self, refresh=False):
        """Return stats related to the printer and the printing job."""
        if refresh or self._job_status is None:
            try:
                job_status = default_request(self._host, PRINTER_STATUS_COMMAND)
            except RuntimeError as exc:
                _LOGGER.exception(str(exc))
                self._job_status = None
            else:
                self._job_status = {
                    DOOR_OPEN[1]: job_status[DOOR_OPEN[0]],
                    CHAMBER_TEMPERATURE[1]: job_status[CHAMBER_TEMPERATURE[0]],
                    ELAPSED_TIME[1]: job_status[ELAPSED_TIME[0]],
                    ESTIMATED_TOTAL_TIME[1]: job_status[ESTIMATED_TOTAL_TIME[0]],
                    EXTRUDER_TEMPERATURE[1]: job_status[EXTRUDER_TEMPERATURE[0]],
                    EXTRUDER_TARGET_TEMPERATURE[1]: job_status[
                        EXTRUDER_TARGET_TEMPERATURE[0]
                    ],
                    FAN_SPEED[1]: job_status[FAN_SPEED[0]],
                    FILAMENT[1]: job_status[FILAMENT[0]],
                    JOB_STATUS[1]: job_status[JOB_STATUS[0]],
                    JOB_NAME[1]: job_status[JOB_NAME[0]],
                    NETWORK_BUILD[1]: job_status[NETWORK_BUILD[0]],
                    PLATFORM_TARGET_TEMPERATURE[1]: job_status[
                        PLATFORM_TARGET_TEMPERATURE[0]
                    ],
                    PLATFORM_TEMPERATURE[1]: job_status[PLATFORM_TEMPERATURE[0]],
                    PROGRESS[1]: job_status[PROGRESS[0]],
                    REMAINING_TIME[1]: job_status[REMAINING_TIME[0]],
                    STATUS[1]: job_status[STATUS[0]],
                }

    def set_extra_status(self, refresh=False):
        """Return extra status that we grab from the Dremel webpage API."""
        if refresh or self._printer_extra_stats is None:
            try:
                extra_status = default_request(
                    self._host,
                    scheme="https",
                    port=EXTRA_STATUS_PORT,
                    path=HOME_MESSAGE_PATH,
                )
                print(extra_status)
            except RuntimeError as exc:
                _LOGGER.exception(str(exc))
                self._printer_extra_stats = None
            else:
                max_platform_temperature = re.search(
                    r"0-(\d+)", extra_status[PLATFORM_TEMPERATURE_RANGE[0]]
                ).group(1)
                max_extruder_temperature = re.search(
                    r"0-(\d+)", extra_status[EXTRUDER_TEMPERATURE_RANGE[0]]
                ).group(1)
                self._printer_extra_stats = {
                    AVAILABLE_STORAGE[1]: extra_status[AVAILABLE_STORAGE[0]],
                    EXTRUDER_TEMPERATURE_RANGE[1]: max_extruder_temperature,
                    PLATFORM_TEMPERATURE_RANGE[1]: max_platform_temperature,
                    USAGE_COUNTER[1]: extra_status[USAGE_COUNTER[0]],
                }

    def refresh(self) -> None:
        """Do a full refresh of all API calls."""
        try:
            self.set_printer_info(refresh=True)
            self.set_job_status(refresh=True)
            self.set_extra_status(refresh=True)
        except RuntimeError as exc:
            _LOGGER.exception(str(exc))

    def get_printer_info(self) -> dict[str, Any]:
        return self._printer_info

    def get_job_status(self) -> dict[str, Any]:
        return (self._job_status or {}) | (self._printer_extra_stats or {})

    def get_manufacturer(self) -> str:
        return DREMEL_MANUFACTURER

    def get_model(self) -> str:
        return self.get_printer_info().get(CONF_MODEL)

    def get_title(self) -> str:
        return self.get_printer_info().get(CONF_TITLE)

    def get_firmware_version(self) -> str:
        return self.get_printer_info().get(CONF_TITLE)

    def is_printing(self) -> bool:
        self.get_printing_status() != "ready" and self.get_printing_status() != "completed"

    def is_paused(self) -> bool:
        self.get_printing_status() == "paused"

    def is_pausing(self) -> bool:
        self.get_printing_status() == "pausing"

    def is_running(self) -> bool:
        self.is_printing() and not self.is_paused() and not self.is_pausing()

    def get_stream_url(self) -> str:
        return f"http://{self._host}:{CAMERA_PORT}/?action=stream"

    def get_snapshot_url(self) -> str:
        return (f"http://{self._host}:{CAMERA_PORT}/?action=snapshot",)

    def get_serial_number(self) -> str:
        return self.get_printer_info().get(CONF_SERIAL_NUMBER)

    def get_printing_status(self) -> str:
        job_status = self.get_job_status().get(JOB_STATUS[1])
        mapped_status = {
            "": "ready",
            "abort": "ready",
            "building": "building",
            "completed": "completed",
            "pausing": "pausing",
            "preparing": "preparing",
            "!pausing": "paused",
            "!resuming": "resuming",
        }
        return mapped_status[job_status] if job_status in mapped_status else "unknown"

    def get_printing_attributes(self) -> dict[str, Any]:
        job_status_attrs = self.get_job_status()
        return {
            key: job_status_attrs[key]
            for key in job_status_attrs.keys()
            & {
                ELAPSED_TIME[1],
                ESTIMATED_TOTAL_TIME[1],
                FAN_SPEED[1],
                FILAMENT[1],
                JOB_NAME[1],
                JOB_STATUS[1],
                NETWORK_BUILD[1],
                REMAINING_TIME[1],
            }
        }

    def get_printing_progress(self) -> float:
        return self.get_job_status().get(PROGRESS[1])

    def get_temperature_type(self, temp_type: str) -> int:
        return self.get_job_status().get(f"{temp_type}_temperature")

    def get_temperature_attributes(self, temp_type: str) -> dict[str, int]:
        return {
            "target_temp": self._job_status.get(f"{temp_type}_target_temperature"),
            "max_temp": int(
                self._printer_extra_stats.get(f"{temp_type}_max_temperature")
            ),
        }

    def _upload_print(self: str, file: str) -> tuple[str, dict[str, str]]:
        try:
            filename = (
                "".join(random.choice(string.ascii_letters) for i in range(10))
                + ".gcode"
            )
            response = requests.post(
                f"http://{self._host}{PRINT_FILE_UPLOADS}",
                files={"print_file": (filename, file)},
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as exc:  # pylint: disable=broad-except
            raise exc
        if error_code := response.status_code != 200:
            raise RuntimeError(f"Upload failed with status code {error_code}")

        return filename

    def _get_print_stats(self, filename: str, data: str) -> dict[str, str]:
        return {
            STATS_FILAMENT_USED: re.search("Filament used: ([0-9.]+)", data).group(1)
            + "m",
            STATS_FILE_NAME: filename,
            STATS_INFILL_SPARSE_DENSITY: re.search(
                "infill_sparse_density = ([0-9.]+)", data
            ).group(1),
            STATS_LAYER_HEIGHT: re.search("Layer height: ([0-9.]+)", data).group(1)
            + "mm",
            STATS_SOFTWARE: re.search("Generated with (.+)", data).group(1),
        }

    def start_print_from_file(self, filepath: str) -> tuple[str, dict[str, str]]:
        """
        Uploads a file to the printer, so it can start a print job. This file is local.
        """
        if (
            filepath is not None
            and os.path.isfile(filepath)
            and filepath.lower().endswith(".gcode")
        ):
            file = open(filepath, "rb")
            data = file.read().decode("utf-8")
            file.seek(0)
        else:
            raise RuntimeError(
                "File path must be defined and point to a valid .gcode file."
            )
        filename = self._upload_print(file)
        try:
            default_request({PRINT_COMMAND: filename})
            return self._get_print_stats(filename, data)
        except RuntimeError as exc:
            _LOGGER.exception(str(exc))

    def start_print_from_url(self, url: str) -> tuple[str, dict[str, str]]:
        """
        Uploads a file to the printer, so it can start a print job. This file is fetched from an URL.
        """
        if url is not None and url.lower().endswith(".gcode"):
            try:
                if validators.url(url) is True:
                    request = requests.get(url, timeout=REQUEST_TIMEOUT)
                elif validators.url(f"https://{url}") is True:
                    try:
                        request = requests.get(
                            f"https://{url}", timeout=REQUEST_TIMEOUT
                        )
                    except requests.exceptions.SSLError:
                        request = requests.get(f"http://{url}", timeout=REQUEST_TIMEOUT)
                else:
                    raise RuntimeError("Invalid URL format")
                if request.status_code != 200:
                    raise RuntimeError(
                        f"URL returned status code {request.status_code}"
                    )
                file = request.content
                data = file.decode("utf-8")
            except requests.exceptions.ConnectionError as exc:
                raise exc
            except Exception as exc:  # pylint: disable=broad-except
                raise exc
        else:
            raise RuntimeError("URL must be defined and be a valid gcode file")
        filename = self._upload_print(file)
        try:
            default_request(self._host, {PRINT_COMMAND: filename})
            return self._get_print_stats(filename, data)
        except RuntimeError as exc:
            _LOGGER.exception(str(exc))

    def resume_print(self) -> dict[str, Any]:
        """Resumes a print job."""
        return default_request(self._host, RESUME_COMMAND)[ERROR_CODE] == 200

    def pause_print(self) -> dict[str, Any]:
        """Pauses a print job."""
        return default_request(self._host, PAUSE_COMMAND)[ERROR_CODE] == 200

    def stop_print(self) -> dict[str, Any]:
        """Stops a print job."""
        return default_request(self._host, CANCEL_COMMAND)[ERROR_CODE] == 200


def default_request(
    host, command="", scheme="http", port=COMMAND_PORT, path=COMMAND_PATH
) -> dict[str, Any]:
    """Performs a default request to the Dremel 3D Printer APIs."""
    url = URL.build(scheme=scheme, host=host, port=port, path=path)

    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    response = requests.post(url, data=command, timeout=REQUEST_TIMEOUT, verify=False)

    response_json = json.loads(response.content.decode("utf-8"))
    if response.status_code != 200:
        raise RuntimeError(
            {
                f"HTTP {response.status_code}",
                {
                    "content-type": response.headers.get("Content-Type"),
                    "message": response_json["message"],
                    "status-code": response.status_code,
                },
            }
        )
    return response_json
