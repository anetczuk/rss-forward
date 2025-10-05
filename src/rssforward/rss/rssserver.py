#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#
#
# Use example of server:
#
# try:
#     server = RSSServerManager()
#     server.port = 8080
#     server.execute(DATA_DIR)
# except KeyboardInterrupt:
#     _LOGGER.info("stopping the server")
#

import os
import logging
import threading
from enum import Enum, unique
from typing import Callable

import socket
import socketserver
import urllib.parse
import posixpath

from http.server import SimpleHTTPRequestHandler


_LOGGER = logging.getLogger(__name__)


## implementation allows to pass custom base path
class RootedHTTPRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        base_path = self.server.base_path  # type: ignore[attr-defined]
        if base_path is None:
            ## no base path given -- standard implementation
            return super().translate_path(path)

        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split("/")
        words = filter(None, words)
        path = base_path
        for word in words:
            _, word = os.path.splitdrive(word)
            # drive, word = os.path.splitdrive(word)
            _, word = os.path.split(word)
            # head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path


## ======================================================


class RSSServer(socketserver.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self.base_path = None


## ======================================================


class RSSServerManager:
    @unique
    class Status(Enum):
        """Server status."""

        STARTED = "Started"
        STOPPED = "Stopped"

    DEFAULT_PORT = 8080
    Handler = RootedHTTPRequestHandler
    # Handler = SimpleHTTPRequestHandler

    def __init__(self):
        socketserver.TCPServer.allow_reuse_address = True
        self.port = RSSServerManager.DEFAULT_PORT
        self.rootDir = None
        self._service: RSSServer = None
        self._thread = None
        self.startedCallback: Callable = None
        self.stoppedCallback: Callable = None
        self.lock = threading.RLock()

    @staticmethod
    def getPrimaryIp():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            sock.connect(("10.255.255.255", 1))
            IP = sock.getsockname()[0] + ":" + str(RSSServerManager.DEFAULT_PORT)
        except BaseException:
            IP = "127.0.0.1" + ":" + str(RSSServerManager.DEFAULT_PORT)
        finally:
            sock.close()
        return IP

    #         hostname = socket.gethostname()
    #         local_ip = socket.gethostbyname(hostname)
    #         return local_ip

    #         return socket.gethostbyname( socket.getfqdn() )

    def getStatus(self) -> "RSSServerManager.Status":
        with self.lock:
            if self._service is not None:
                return RSSServerManager.Status.STARTED
            return RSSServerManager.Status.STOPPED

    def switchState(self, new_state):
        if new_state:
            _LOGGER.info("starting server")
            self.start()
        else:
            _LOGGER.info("stopping server")
            self.stop()

    # asynchronous call
    # 'rootDir' - path to directory containing RSS feeds (feeds can be in any subfolder)
    # relative path will be reflected in URL address of the feed
    def start(self, rootDir=None):
        with self.lock:
            if self._service is not None:
                ## already started
                return
            if rootDir:
                self.rootDir = rootDir
            self._thread = threading.Thread(target=self._run, args=[])
            self._thread.start()

    def stop(self):
        with self.lock:
            if self._service is None:
                ## not started
                return
            _LOGGER.info("stopping feed server")
            self._shutdownService()
            self._thread.join()
            self._thread = None

    def join(self):
        self._thread.join()

    # blocking execution
    # 'rootDir' - path to directory containing RSS feeds (feeds can be in any subfolder)
    # relative path will be reflected in URL address of the feed
    def execute(self, rootDir=None):
        with self.lock:
            if rootDir:
                self.rootDir = rootDir
            self._run()

    def _run(self):
        try:
            with RSSServer(("", self.port), RSSServerManager.Handler) as httpd:
                #         with socketserver.TCPServer(("", self.port), RSSServerManager.Handler) as httpd:
                if self.rootDir:
                    os.makedirs(self.rootDir, exist_ok=True)
                self._service = httpd
                self._service.base_path = self.rootDir
                try:
                    _LOGGER.info("serving at port %s", self.port)
                    httpd.allow_reuse_address = True
                    self._notifyStarted()
                    httpd.serve_forever()
                #             httpd.handle_request()
                finally:
                    self._service.server_close()
                    self._service = None
                    self._notifyStopped()
            _LOGGER.info("server thread ended")
        except OSError:
            _LOGGER.exception("unable to start server on port: %s", self.port)
            raise
        except:  # noqa
            _LOGGER.exception("unhandled exception occur - terminating server thread")
            raise

    def _shutdownService(self):
        if self._service is None:
            return
        self._service.shutdown()

    def _notifyStarted(self):
        if not callable(self.startedCallback):
            return
        # pylint: disable=E1102
        self.startedCallback()

    def _notifyStopped(self):
        if not callable(self.stoppedCallback):
            return
        # pylint: disable=E1102
        self.stoppedCallback()
