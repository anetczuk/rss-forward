#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging

import pystray
from PIL import Image


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


_LOGGER = logging.getLogger(__name__)

logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)


class TrayManager:
    def __init__(self, *, server_state=True):
        self._server_state: bool = server_state
        ## new_state values:
        ##    - negative - invalid
        ##    - 0 - in progress
        ##    - positive - succeed
        self._valid_state: int = 0
        self.server_callback = None
        self.refresh_callback = None
        self.open_log_callback = None

        self.red_icon_image = load_icon("rss-forward-red-64.png")
        self.yellow_icon_image = load_icon("rss-forward-yellow-64.png")
        self.green_icon_image = load_icon("rss-forward-green-64.png")
        self.blue_icon_image = load_icon("rss-forward-blue-64.png")
        self.gray_icon_image = load_icon("rss-gray-64.png")

        rss_server_item = pystray.MenuItem(
            "Run RSS Server",
            self._on_rss_server_clicked,
            checked=lambda _item: self._server_state,
        )

        rss_refresh_item = pystray.MenuItem("Refresh RSS", self._on_refresh_clicked)
        open_log_item = pystray.MenuItem("Open log", self._on_open_log_clicked)
        quit_item = pystray.MenuItem("Quit", self._on_quit_clicked)

        menu = pystray.Menu(rss_server_item, rss_refresh_item, open_log_item, quit_item)

        self.tray_icon = pystray.Icon(name="rss-forward", title="RSS Forward", menu=menu)
        self._set_icon()

    @property
    def server_state(self):
        return self._server_state

    @server_state.setter
    def server_state(self, new_state):
        self._server_state = new_state
        self._set_icon()

    @property
    def is_error(self):
        return self._valid_state < 0

    @is_error.setter
    def is_error(self, new_state: bool):
        if new_state:
            self._valid_state = 1
        else:
            self._valid_state = -1
        self._set_icon()

    ##self.yellow_icon_image

    # ruff: noqa: FBT001
    def set_valid(self, new_state: bool):
        self.is_error = not new_state

    ## new_state values:
    ##    - negative - invalid
    ##    - 0 - in progress
    ##    - positive - succeed
    def set_state(self, new_state: int):
        self._valid_state = new_state
        self._set_icon()

    def _set_icon(self):
        if self._valid_state < 0:
            _LOGGER.info("error detected - setting red icon")
            self.tray_icon.icon = self.red_icon_image
            return
        if self._valid_state == 0:
            _LOGGER.info("in progress - setting yellow icon")
            self.tray_icon.icon = self.yellow_icon_image
            return
        if self._server_state:
            _LOGGER.info("server operational - setting blue icon")
            self.tray_icon.icon = self.blue_icon_image
        else:
            _LOGGER.info("server disabled - setting green icon")
            self.tray_icon.icon = self.green_icon_image

    def run_loop(self):
        """Execute event loop. Method have to be executed from main thread."""
        _LOGGER.info("starting systray loop")
        self.tray_icon.run()

    # =================================================

    # set callback for enable/disable RSS server
    def set_rss_server_callback(self, callback):
        self.server_callback = callback

    # set "refresh" callback
    def set_refresh_callback(self, callback):
        self.refresh_callback = callback

    # set open log callback
    def set_open_log_callback(self, callback):
        self.open_log_callback = callback

    # =================================================

    def _on_rss_server_clicked(self, _icon, item):  # pylint: disable=W0613
        self._server_state = not item.checked
        self._set_icon()
        # icon.notify("server clicked")
        _LOGGER.info("server clicked to state %s", self._server_state)
        if self.server_callback is None:
            _LOGGER.info("server callback not set")
            return
        self.server_callback(self._server_state)

    def _on_refresh_clicked(self, _icon, _item):  # pylint: disable=W0613
        _LOGGER.info("refresh clicked")
        # icon.notify("refresh clicked")
        if self.refresh_callback is None:
            _LOGGER.info("refresh callback not set")
            return
        self.refresh_callback()

    def _on_open_log_clicked(self, _icon, _item):  # pylint: disable=W0613
        _LOGGER.info("open log clicked")
        # icon.notify("refresh clicked")
        if self.open_log_callback is None:
            _LOGGER.info("log callback not set")
            return
        self.open_log_callback()

    def _on_quit_clicked(self, icon, _item):  # pylint: disable=W0613
        _LOGGER.info("quit clicked")
        icon.remove_notification()
        self.tray_icon.stop()


# ================================================================


def load_icon(icon_name):
    icon_path = os.path.join(SCRIPT_DIR, icon_name)
    icon_path = os.path.abspath(icon_path)
    return Image.open(icon_path)
