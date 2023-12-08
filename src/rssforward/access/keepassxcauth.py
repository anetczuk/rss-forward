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

from pathlib import Path

from keepassxc_browser import Connection, Identity, ProtocolError

from rssforward.utils import get_app_datadir


_LOGGER = logging.getLogger(__name__)


class LockedKPXCException(Exception):
    pass


class KeepassxcAuth:
    def __init__(self):
        assoc_dir = get_app_datadir()
        # assoc_dir = tempfile.gettempdir()
        state_path = os.path.join(assoc_dir, ".assoc")
        self.state_file = None
        self.state_file = Path(state_path)  # state file reduces number of authentications

        self.id = None
        self.connection = None

        client_id = "rss-forward"
        if self.state_file and self.state_file.exists():
            with self.state_file.open("r", encoding="utf-8") as f:
                data = f.read()
            self.id = Identity.unserialize(client_id, data)
        else:
            self.id = Identity(client_id)
            _LOGGER.info("Initializing new state")

    def connect(self):
        try:
            self.connection = Connection("kpxc_server")
        except OSError:
            _LOGGER.error("Unable to find keepassxc socket. Try different or default value of 'socket_name'.")
            raise

        self.connection.connect()
        self.connection.change_public_keys(self.id)

    def disconnect(self):
        self._checkConnection()
        self.connection.disconnect()
        self.connection = None

    def unlockDatabase(self):
        self._checkConnection()

        if not self.isDatabaseOpen():
            _LOGGER.info("Waiting for database open")
            self.connection.wait_for_unlock()

        if not self.connection.test_associate(self.id):
            _LOGGER.info("Associating application")
            if not self.connection.associate(self.id):
                raise RuntimeError("could not associate")
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
            _LOGGER.warning("exception occur while checking if database is open: %s", exc)

        # there is problem with connection state after connecting - workaround is to reconnect
        self.disconnect()
        self.connect()
        return False

    def getAuthData(self, access_url):
        self._checkConnection()
        login = {}
        try:
            logins = self.connection.get_logins(self.id, url=access_url)
            if len(logins) != 1:
                raise RuntimeError("could not get login data")
            data = logins[0]
            login = {"login": data.get("login"), "password": data.get("password")}
        except ProtocolError as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            raise LockedKPXCException() from exc
        except AssertionError as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            raise LockedKPXCException() from exc
        return login

    def _checkConnection(self):
        if self.connection is None:
            raise Exception("not connected")


auth = None


def get_auth_data(access_url):
    global auth  # pylint: disable=W0603
    if not auth:
        auth = KeepassxcAuth()
        auth.connect()
        auth.unlockDatabase()

    while True:
        try:
            login_data = auth.getAuthData(access_url)
            if login_data:
                return login_data
        except LockedKPXCException as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            time.sleep(1)

    return {}
