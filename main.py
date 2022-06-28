# import the necessary packages
import argparse
import asyncio
import atexit
import json
import logging
import os
import signal
import sys
from io import BytesIO
from time import sleep

import imageio
from PIL import Image

from dremel3dpy import Dremel3DPrinter
from dremel3dpy.camera import Dremel3D45Timelapse
from dremel3dpy.helpers.constants import (
    _LOGGER,
    DEFAULT_FPS,
    DEFAULT_MAX_SIZE_MB,
    DEFAULT_SCALE_PERCENT,
    EXIT_SIGNALS,
)

# sys.tracebacklimit = 0


def parse_arguments():
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="Host to the Dremel 3D Printer.")
    ap.add_argument("--info", help="Prints printer info.", action="store_true")
    ap.add_argument("--job", help="Prints job info.", action="store_true")

    group = ap.add_mutually_exclusive_group()
    group.add_argument("--pause", help="Pause a printing job.", action="store_true")
    group.add_argument("--resume", help="Resume a printing job.", action="store_true")
    group.add_argument("--stop", help="Stop a printing job.", action="store_true")
    group.add_argument("--print", help="Print a gcode file.", action="store_true")

    logging_group = ap.add_mutually_exclusive_group()
    logging_group.add_argument(
        "-d",
        "--debug",
        help="Print lots of debugging statements.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    logging_group.add_argument(
        "-v",
        "--verbose",
        help="Be verbose.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    source_group = ap.add_mutually_exclusive_group()
    source_group.add_argument(
        "--filepath",
        help="Filepath where the gcode file to print is located.",
        type=str,
    )
    source_group.add_argument(
        "--url",
        help="URL where the gcode file to print is located.",
        type=str,
    )

    output_type_group = ap.add_mutually_exclusive_group()
    output_type_group.add_argument(
        "--gif",
        help="Create a gif timelapse of the printing job. Only records while the printer is busy printing.",
        action="store_true",
        default=False,
    )
    output_type_group.add_argument(
        "--snapshot",
        help="Takes a snapshot of the camera and saves it to the output file.",
        action="store_true",
        default=False,
    )

    runtime_group = ap.add_argument_group()
    runtime_group.add_argument(
        "--silent",
        help="Whether to not show the progress bars, specially util for non-TTY usage.",
        action="store_true",
        default=False,
    )
    runtime_group.add_argument(
        "--idle",
        help="Keeps creating the gif even if the printer is idle.",
        action="store_true",
        default=False,
    )

    timelapse_group = ap.add_mutually_exclusive_group()
    timelapse_group.add_argument(
        "--duration",
        help="Duration in seconds of your final media. Regardless of this duration, the media will capture the entire printing job. So for instance if it takes 1 hour to print a file and your --duration is 10 seconds, your final gif will have a timelapse of 10 seconds showing the entire printing job.",
        type=int,
    )
    timelapse_group.add_argument(
        "--length",
        help="How many seconds you want to record a given gif. Your final media will have --length amount of seconds, with --fps frames per second, but the timelapse will have --length seconds. If you want to have a media output with a given duration but have it record the entire timelapse of the printing job, use the option --duration instead.",
        type=int,
    )
    timelapse_group.add_argument(
        "--runtime",
        help="This is different than --duration and --length in a way that it lets you define the number of seconds your script will run for. It doesn't determine the length or size of the media produced, just gives you control over the execution runtime limit of this program.",
        default=None,
        type=int,
    )

    media_group = ap.add_argument_group()
    media_group.add_argument(
        "--output",
        help="Output path to save the timelapse gif.",
        type=str,
    )
    media_group.add_argument(
        "--max-output-size",
        help="Maximum size in MB of the output gif.",
        type=float,
        default=DEFAULT_MAX_SIZE_MB,
    )
    media_group.add_argument(
        "--fps",
        help="FPS for the generated timelapse gif.",
        default=DEFAULT_FPS,
        type=int,
    )
    media_group.add_argument(
        "--original",
        help="If true, won't display a canvas with the progress status and will leave the frames intact.",
        action="store_true",
        default=False,
    )
    media_group.add_argument(
        "--scale",
        help="How much to scale the dimensions of the frames. Scaling down dramatically decreases output size.",
        type=float,
        default=DEFAULT_SCALE_PERCENT,
    )

    args = ap.parse_args()

    if (args.gif or args.snapshot) and args.output is None:
        ap.error("When --gif or --snapshot are defined, you must also define --output.")
    if not args.print and (args.filepath is not None or args.url is not None):
        ap.error("--filepath or --url are arguments used together with --print.")
    if args.print and args.filepath is None and args.url is None:
        ap.error("--print requires either --filepath or --url to be defined.")
    if args.idle:
        # Force silent to be True if running on idle mode
        args.silent = True

    return args


def graceful_shutdown(camera):
    _LOGGER.info("Gracefully shutting down.")
    remove_signals_to_loop()
    camera.stop_timelapse()
    if loop.is_running():
        [task.cancel() for task in asyncio.all_tasks(loop)]
    loop.stop()
    if not loop.is_running():
        loop.close()


def shutdown_with_signal(camera, signal):
    _LOGGER.exception(f"Received exit signal {signal.name}...")
    graceful_shutdown(camera)


def exception_handler(camera):
    graceful_shutdown(camera)


def add_signals_to_loop(camera):
    for s in EXIT_SIGNALS:
        loop.add_signal_handler(s, lambda s=s: shutdown_with_signal(camera, s))


def remove_signals_to_loop():
    for s in EXIT_SIGNALS:
        loop.remove_signal_handler(s)


async def make_gif(
    camera,
    output,
    fps,
    max_output_size,
    duration,
    length,
    idle,
    original,
    scale,
    silent,
):
    return await camera.start_timelapse(
        output,
        fps,
        max_output_size,
        duration,
        length,
        idle,
        original,
        scale,
        silent or idle,
    )


def make_snapshot(camera, output, original, scale):
    snapshot = camera.get_snapshot_as_ndarray(original, scale)
    image = Image.fromarray(snapshot)
    image.save(output)


async def main():
    args = parse_arguments()
    logging.basicConfig(
        level=args.loglevel if args.loglevel is not None else logging.ERROR
    )

    host = args.host
    dremel = Dremel3DPrinter(host)

    if args.info:
        print(json.dumps(dremel.get_printer_info(), indent=2))
    if args.job:
        print(json.dumps(dremel.get_job_status(), indent=2))

    if args.pause:
        dremel.pause_print()
        loop.stop()
    elif args.resume:
        dremel.resume_print()
        loop.stop()
    elif args.stop:
        dremel.stop_print()
        loop.stop()
    else:
        if args.print:
            if args.filepath:
                dumps = json.dumps(
                    dremel.start_print_from_file(args.filepath), indent=2
                )
                print(dumps)
            elif args.url:
                dumps = json.dumps(dremel.start_print_from_url(args.url), indent=2)
                print(dumps)

        if args.gif or args.snapshot:
            if dremel.get_model() != "3D45":
                raise RuntimeError(
                    "You can only use media resources such as creating gif or taking a snapshot with the 3D45 model, which has an embedded camera."
                )
            camera = Dremel3D45Timelapse(dremel, loop)
            group = []
            try:
                if args.snapshot:
                    make_snapshot(camera, args.output, args.original, args.scale)
                    camera.stop_timelapse()
                elif args.gif:
                    loop.set_exception_handler(lambda s, c: exception_handler(camera))
                    add_signals_to_loop(camera)
                    group += [
                        asyncio.wait_for(
                            make_gif(
                                camera,
                                args.output,
                                args.fps,
                                args.max_output_size,
                                args.duration,
                                args.length,
                                args.idle,
                                args.original,
                                args.scale,
                                args.silent,
                            ),
                            args.runtime,
                        )
                    ]
                    await asyncio.gather(*group)
            except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
                _LOGGER.exception("Execution interrupted.")
            except Exception:
                _LOGGER.exception("Unexpected exception.")
            finally:
                graceful_shutdown(camera)
        else:
            loop.stop()


loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
