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


class TrayManager:
    def __init__(self, server_state=True):
        self._server_state = server_state
        self.server_callback = None
        self.refresh_callback = None
        self.open_log_callback = None

        red_icon_path = os.path.join(SCRIPT_DIR, "rss-forward-red-64.png")
        red_icon_path = os.path.abspath(red_icon_path)
        self.red_icon_image = Image.open(red_icon_path)

        blue_icon_path = os.path.join(SCRIPT_DIR, "rss-forward-blue-64.png")
        blue_icon_path = os.path.abspath(blue_icon_path)
        self.blue_icon_image = Image.open(blue_icon_path)

        rss_server_item = pystray.MenuItem(
            "Run RSS Server", self._onRSSServerClicked, checked=lambda item: self._server_state
        )

        rss_refresh_item = pystray.MenuItem("Refresh RSS", self._onRefreshClicked)
        open_log_item = pystray.MenuItem("Open log", self._onOpenLogClicked)
        quit_item = pystray.MenuItem("Quit", self._onQuitClicked)

        menu = pystray.Menu(rss_server_item, rss_refresh_item, open_log_item, quit_item)

        self.tray_icon = pystray.Icon(name="rss-forward", title="RSS Forward", menu=menu)
        self._setIcon()

    @property
    def server_state(self):
        return self._server_state

    @server_state.setter
    def server_state(self, new_state):
        self._server_state = new_state
        self._setIcon()

    def _setIcon(self):
        if self._server_state:
            self.tray_icon.icon = self.blue_icon_image
        else:
            self.tray_icon.icon = self.red_icon_image

    def runLoop(self):
        """Execute event loop. Method have to be executed from main thread."""
        _LOGGER.info("starting systray loop")
        self.tray_icon.run()

    # =================================================

    def setRSSServerCallback(self, callback):
        self.server_callback = callback

    def setRefreshCallback(self, callback):
        self.refresh_callback = callback

    def setOpenLogCallback(self, callback):
        self.open_log_callback = callback

    # =================================================

    def _onRSSServerClicked(self, icon, item):  # pylint: disable=W0613
        self._server_state = not item.checked
        self._setIcon()
        # icon.notify("server clicked")
        _LOGGER.info("server clicked to state %s", self._server_state)
        if self.server_callback:
            self.server_callback(self._server_state)

    def _onRefreshClicked(self, icon, item):  # pylint: disable=W0613
        _LOGGER.info("refresh clicked")
        # icon.notify("refresh clicked")
        if self.refresh_callback:
            self.refresh_callback()

    def _onOpenLogClicked(self, icon, item):  # pylint: disable=W0613
        _LOGGER.info("open log clicked")
        # icon.notify("refresh clicked")
        if self.open_log_callback:
            self.open_log_callback()

    def _onQuitClicked(self, icon, item):  # pylint: disable=W0613
        _LOGGER.info("quit clicked")
        icon.remove_notification()
        self.tray_icon.stop()
