#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import sys
import os
import logging
import argparse
import time
import subprocess  # nosec

from rssforward import logger
from rssforward.rss.rssserver import RSSServerManager
from rssforward.rssmanager import RSSManager, ThreadedRSSManager
from rssforward.configfile import load_config, ConfigField, ConfigKey
from rssforward.systray.traymanager import TrayManager


_LOGGER = logging.getLogger(__name__)


def start_with_tray(parameters):
    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    data_root = general_section.get(ConfigField.DATAROOT.value)
    log_dir = general_section.get(ConfigField.LOGDIR.value)
    log_viewer = general_section.get(ConfigField.LOGVIEWER.value)
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)
    start_server = general_section.get(ConfigField.STARTSERVER.value, True)
    rss_port = general_section.get(ConfigField.PORT.value, 8080)
    genloop = general_section.get(ConfigField.GENLOOP.value, True)
    startupdelay = general_section.get(ConfigField.STARTUPDELAY.value, 0)

    tray_manager = TrayManager(server_state=start_server)

    # async start of RSS server
    rss_server = RSSServerManager()
    rss_server.port = rss_port
    rss_server.rootDir = data_root

    if start_server:
        rss_server.start()
    else:
        _LOGGER.info("starting RSS server disabled")

    manager = RSSManager(parameters)
    threaded_manager = ThreadedRSSManager(manager)

    tray_manager.setRSSServerCallback(rss_server.switchState)
    tray_manager.setRefreshCallback(threaded_manager.executeSingle)

    threaded_manager.setStateCallback(tray_manager.setValid)

    log_path = os.path.join(log_dir, "log.txt")
    tray_manager.setOpenLogCallback(lambda: open_log(log_viewer, log_path))

    # data generation main loop
    exit_code = 0
    try:
        if startupdelay > 0:
            _LOGGER.info("waiting %s seconds (startup delay)", startupdelay)
            time.sleep(startupdelay)

        if genloop:
            threaded_manager.start(refresh_time)
        else:
            # generate data
            _LOGGER.info("generating RSS data only once")
            manager.generateData()

        tray_manager.runLoop()  # run tray main loop

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")

    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        exit_code = 1

    finally:
        manager.close()
        threaded_manager.stop()
        threaded_manager.join()
        rss_server.stop()

    return exit_code


def start_no_tray(parameters):
    """Start generation with RSS server."""
    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    data_root = general_section.get(ConfigField.DATAROOT.value)
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)
    rss_port = general_section.get(ConfigField.PORT.value, 8080)
    genloop = general_section.get(ConfigField.GENLOOP.value, True)
    startupdelay = general_section.get(ConfigField.STARTUPDELAY.value, 0)

    # async start of RSS server
    rss_server = RSSServerManager()
    rss_server.port = rss_port
    rss_server.start(data_root)

    manager = RSSManager(parameters)
    threaded_manager = ThreadedRSSManager(manager)

    # data generation main loop
    exit_code = 0
    try:
        if startupdelay > 0:
            _LOGGER.info("waiting %s seconds (startup delay)", startupdelay)
            time.sleep(startupdelay)

        if genloop:
            threaded_manager.executeLoop(refresh_time)
        else:
            # generate data and keep server running
            _LOGGER.info("generating RSS data only once")
            manager.generateData()
            rss_server.join()

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")

    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        exit_code = 1

    finally:
        rss_server.stop()

    return exit_code


def start_raw(parameters):
    """Start raw generation loop."""
    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)
    genloop = general_section.get(ConfigField.GENLOOP.value, True)
    startupdelay = general_section.get(ConfigField.STARTUPDELAY.value, 0)

    manager = RSSManager(parameters)
    threaded_manager = ThreadedRSSManager(manager)

    # data generation main loop
    exit_code = 0
    try:
        if startupdelay > 0:
            _LOGGER.info("waiting %s seconds (startup delay)", startupdelay)
            time.sleep(startupdelay)

        if genloop:
            threaded_manager.executeLoop(refresh_time)
        else:
            # generate data and exit
            _LOGGER.info("generating RSS data only once")
            manager.generateData()

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")

    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        exit_code = 1

    return exit_code


def open_log(log_viewer, log_path):
    try:
        command = log_viewer % log_path
    except TypeError:
        _LOGGER.exception("unable to run logger, command: %s log path: %s", log_viewer, log_path)
        return
    _LOGGER.info("opening log viewer: %s", command)
    with subprocess.Popen(command, shell=True):  # nosec
        pass


# ============================================================


def str_to_bool(value):
    if value.lower() in ("true", "t", "yes", "y"):
        return True
    if value.lower() in ("false", "f", "no", "n"):
        return False
    raise argparse.ArgumentTypeError("boolean value expected")


def main():
    parser = argparse.ArgumentParser(description="RSS Forward", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--config", action="store", required=False, help="Path to TOML config file")
    parser.add_argument(
        "--trayicon",
        choices=["True", "False"],
        type=str_to_bool,
        default=None,
        required=False,
        help="Use system tray icon (overrides config 'trayicon' option)",
    )
    parser.add_argument(
        "--startserver",
        choices=["True", "False"],
        type=str_to_bool,
        default=None,
        required=False,
        help="Enable RSS server at startup (overrides config 'startserver' option)",
    )
    parser.add_argument(
        "--genloop",
        choices=["True", "False"],
        type=str_to_bool,
        default=None,
        required=False,
        help="Use RSS generator loop or scrap RSS data only once at startup (overrides config 'genloop' option)",
    )
    parser.add_argument(
        "--startupdelay",
        type=int,
        default=None,
        required=False,
        help="Set delay in seconds before first generation (useful on startup to wait for KeePassXC to start before)",
    )

    args = parser.parse_args()

    parameters = load_config(args.config)

    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    log_dir = general_section.get(ConfigField.LOGDIR.value)
    logger.configure(logDir=log_dir)

    _LOGGER.info("============================== starting application ==============================")
    _LOGGER.info("Log output dir: %s", log_dir)

    data_root = general_section.get(ConfigField.DATAROOT.value)
    _LOGGER.info("RSS data root dir: %s", data_root)

    if args.trayicon is not None:
        general_section[ConfigField.TRAYICON.value] = args.trayicon
    if args.startserver is not None:
        general_section[ConfigField.STARTSERVER.value] = args.startserver
    if args.genloop is not None:
        general_section[ConfigField.GENLOOP.value] = args.genloop
    if args.startupdelay is not None:
        general_section[ConfigField.STARTUPDELAY.value] = args.startupdelay

    tray_icon = general_section.get(ConfigField.TRAYICON.value, True)

    if tray_icon:
        _LOGGER.info("starting with tray")
        exit_code = start_with_tray(parameters)
        sys.exit(exit_code)
        return

    _LOGGER.info("starting without system tray")
    start_server = general_section.get(ConfigField.STARTSERVER.value, True)
    if start_server:
        exit_code = start_no_tray(parameters)
        sys.exit(exit_code)
        return

    _LOGGER.info("starting RSS server disabled")
    exit_code = start_raw(parameters)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
