#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
import time
import socket

from pathlib import Path

from keepassxc_browser import Connection, Identity, ProtocolError

from rssforward.utils import get_app_datadir


_LOGGER = logging.getLogger(__name__)


class LockedKPXCError(Exception):
    pass


class KeepassxcAuth:
    def __init__(self, client_id=None, state_file_path=None):
        if state_file_path is None:
            assoc_dir = get_app_datadir()
            # assoc_dir = tempfile.gettempdir()
            state_file_path = os.path.join(assoc_dir, ".assoc")
        self.state_file = None
        self.state_file = Path(state_file_path)  # state file reduces number of authentications

        self.id = None
        self.connection = None

        if client_id is None:
            client_id = "rss-forward"
        if self.state_file and self.state_file.exists():
            with self.state_file.open("r", encoding="utf-8") as f:
                data = f.read()
            self.id = Identity.unserialize(client_id, data)
        else:
            self.id = Identity(client_id)
            _LOGGER.info("Initializing new state")

    def connect(self):
        self.connection = self._establishConnection("kpxc_server")
        if not self.connection:
            self.connection = self._establishConnection()
        if not self.connection:
            message = "Unable to find keepassxc socket. Try different value of 'socket_name'."
            raise RuntimeError(message)

        self.connection.connect()
        self.connection.change_public_keys(self.id)

    def disconnect(self):
        self._checkConnection()
        self.connection.connection.sock.shutdown(socket.SHUT_RDWR)
        self.connection.disconnect()
        self.connection = None

    def getHash(self):
        return self.connection.get_database_hash(self.id)

    def unlockDatabase(self):
        self._checkConnection()

        if not self.isDatabaseOpen():
            # there is weird behaviour: after unlocking in KeepassXC and receiving "unlock" signal
            # "isDatabaseOpen()" returns False and ask KeePassXC to authenticate again
            # workaround is to ask again if database is open before waiting for unlock
            self.isDatabaseOpen()

            _LOGGER.info("Waiting for database open")
            self.connection.wait_for_unlock()
            _LOGGER.info("database unlocked")

        if not self.connection.test_associate(self.id):
            _LOGGER.info("Associating application")

            # will raise exception AssertionError: {'action': 'database-locked'}
            # if KeePass is configured to lock database on minimalization
            if not self.connection.associate(self.id):
                message = "could not associate"
                raise RuntimeError(message)
            if self.state_file:
                data = self.id.serialize()
                with self.state_file.open("w", encoding="utf-8") as f:
                    f.write(data)
                del data

    def lockDatabase(self):
        self._checkConnection()
        self.connection.lock_database(self.id)

    def isDatabaseOpen(self):
        self._checkConnection()
        try:
            return self.connection.is_database_open(self.id)
        except AssertionError as exc:
            if "database-locked" in str(exc):
                return False
            _LOGGER.warning("exception occur while checking if database is open: %s", exc)
        return False

    def getAuthData(self, access_url):
        self._checkConnection()
        self.unlockDatabase()
        login = {}
        try:
            logins = self.connection.get_logins(self.id, url=access_url)
            if len(logins) != 1:
                message = "could not get login data"
                raise RuntimeError(message)
            data = logins[0]
            login = {"login": data.get("login"), "password": data.get("password")}
        except ProtocolError as exc:
            _LOGGER.exception("failed to get auth data")
            raise LockedKPXCError from exc
        except AssertionError as exc:
            _LOGGER.exception("failed to get auth data")
            raise LockedKPXCError from exc
        return login

    def _checkConnection(self):
        if self.connection is None:
            message = "not connected"
            raise RuntimeError(message)

    def _establishConnection(self, socket_name=None):
        try:
            if socket_name:
                return Connection(socket_name)
            return Connection()
        except OSError:
            return None


auth: KeepassxcAuth = None


def get_auth_data(access_url):
    # ruff: noqa: PLW0603
    global auth  # pylint: disable=W0603
    if not auth:
        for _i in range(3):
            try:
                auth = KeepassxcAuth()
                auth.connect()
                auth.unlockDatabase()
                break
            except Exception:  # # pylint: disable=W0718
                _LOGGER.exception("failed to unlock database, retrying")
                time.sleep(1.0)
        else:
            # loop finished without database unlock
            message = "failed to unlock database"
            raise RuntimeError(message)

    while True:
        try:
            login_data = auth.getAuthData(access_url)
            if login_data:
                return login_data

        # ruff: noqa: PERF203
        except LockedKPXCError as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            time.sleep(1)

        except BrokenPipeError as exc:
            _LOGGER.info("failed to get auth data: %s, retrying", exc)
            time.sleep(1)

    return {}


def close():
    # ruff: noqa: PLW0602
    global auth  # pylint: disable=W0602
    if auth:
        _LOGGER.info("closing keepass connection")
        auth.disconnect()
