#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import sys
import logging
import argparse

from rssforward import logger
from rssforward.rss.rssserver import RSSServerManager
from rssforward.rssmanager import RSSManager, ThreadedRSSManager
from rssforward.configfile import load_config, ConfigField, ConfigKey
from rssforward.systray.traymanager import TrayManager


_LOGGER = logging.getLogger(__name__)


def start_with_tray(parameters):
    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    data_root = general_section.get(ConfigField.DATAROOT.value)

    # async start of RSS server
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)
    start_server = general_section.get(ConfigField.STARTSERVER.value, True)

    tray_manager = TrayManager(server_state=start_server)

    rss_port = general_section.get(ConfigField.PORT.value, 8080)
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

    exit_code = 0

    # data generation main loop
    try:
        threaded_manager.start(refresh_time)

        tray_manager.runLoop()  # run tray main loop

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")

    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        exit_code = 1

    finally:
        threaded_manager.stop()
        threaded_manager.join()
        rss_server.stop()

    return exit_code


def start_no_tray(parameters):
    """Start generation with RSS server."""
    general_section = parameters.get(ConfigKey.GENERAL.value, {})
    data_root = general_section.get(ConfigField.DATAROOT.value)

    # async start of RSS server
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)

    rss_port = general_section.get(ConfigField.PORT.value, 8080)
    rss_server = RSSServerManager()
    rss_server.port = rss_port
    rss_server.start(data_root)

    manager = RSSManager(parameters)
    threaded_manager = ThreadedRSSManager(manager)
    exit_code = 0

    # data generation main loop
    try:
        threaded_manager.executeLoop(refresh_time)

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

    # async start of RSS server
    refresh_time = general_section.get(ConfigField.REFRESHTIME.value, 3600)

    _LOGGER.info("starting RSS server disabled")

    manager = RSSManager(parameters)
    threaded_manager = ThreadedRSSManager(manager)
    exit_code = 0

    # data generation main loop
    try:
        threaded_manager.executeLoop(refresh_time)

    except KeyboardInterrupt:
        _LOGGER.info("keyboard interrupt detected - stopping")

    except:  # noqa pylint: disable=W0702
        _LOGGER.exception("unhandled exception detected - exiting")
        exit_code = 1

    return exit_code


# ============================================================


def main():
    parser = argparse.ArgumentParser(description="RSS Forward")
    parser.add_argument("-c", "--config", action="store", required=False, default="", help="Path to TOML config file")
    parser.add_argument(
        "--no-tray",
        action="store_true",
        required=False,
        help="Do not use system tray icon (overrides config 'trayicon' option)",
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        required=False,
        help="Do not run RSS server (overrides config 'startserver' option)",
    )

    args = parser.parse_args()

    logger.configure()

    parameters = load_config(args.config)

    general_section = parameters.get(ConfigKey.GENERAL.value, {})

    data_root = general_section.get(ConfigField.DATAROOT.value)
    _LOGGER.info("RSS data root dir: %s", data_root)

    if args.no_tray:
        general_section[ConfigField.TRAYICON.value] = False
    if args.no_server:
        general_section[ConfigField.STARTSERVER.value] = False

    tray_icon = general_section.get(ConfigField.TRAYICON.value, True)

    if tray_icon:
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
