#!/usr/bin/python3
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
import tempfile
from pathlib import Path

from keepassxc_browser import Connection, Identity, ProtocolError


_LOGGER = logging.getLogger(__name__)


class LockedKPXCException(Exception):
    pass


class KeepassxcAuth:
    def __init__(self):
        self.client_id = "rss-forward"
        tmp_dir = tempfile.gettempdir()
        state_path = os.path.join(tmp_dir, ".assoc")
        self.state_file = Path(state_path)  # state file reduces number of authentications
        # self.state_file = Path('.assoc')        # state file reduces number of authentications
        self.connection = None
        self.connection = Connection()
        self.id = None

        if self.state_file and self.state_file.exists():
            with self.state_file.open("r", encoding="utf-8") as f:
                data = f.read()
            self.id = Identity.unserialize(self.client_id, data)
        else:
            self.id = Identity(self.client_id)
            _LOGGER.info("Initializing new state")

    def connect(self):
        self.connection.connect()
        self.connection.change_public_keys(self.id)

        if not self.isDatabaseOpen():
            _LOGGER.info("Waiting for database open")
            while not self.isDatabaseOpen():
                time.sleep(1)

        if not self.connection.test_associate(self.id):
            _LOGGER.info("Associating application")
            if not self.connection.associate(self.id):
                raise RuntimeError("could not associate")
            if self.state_file:
                data = self.id.serialize()
                with self.state_file.open("w", encoding="utf-8") as f:
                    f.write(data)
                del data

    def isDatabaseOpen(self):
        try:
            return self.connection.is_database_open(self.id)
        except AssertionError as exc:
            _LOGGER.warning("exception occur while checking if database is open: %s", exc)
            # there is problem with connection state after connecting - workaround is to reconnect
            self.disconnect()
            self.connect()
            return False

    def lockDatabase(self):
        self.connection.lock_database(self.id)

    def getAuthData(self, access_url):
        login = {}
        try:
            logins = self.connection.get_logins(self.id, url=access_url)
            if len(logins) != 1:
                raise RuntimeError("could not get login data")
            data = logins[0]
            login = {"login": data.get("login"), "password": data.get("password")}
        except ProtocolError as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            raise LockedKPXCException()
        except AssertionError as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            raise LockedKPXCException()
        return login

    def disconnect(self):
        self.connection.disconnect()


auth = None


def get_auth_data(access_url):
    global auth  # pylint: disable=W0603
    if not auth:
        auth = KeepassxcAuth()
        auth.connect()

    while True:
        try:
            login_data = auth.getAuthData(access_url)
            if login_data:
                return login_data
        except LockedKPXCException as exc:
            _LOGGER.warning("failed to get auth data: %s", exc)
            time.sleep(1)

    return {}
