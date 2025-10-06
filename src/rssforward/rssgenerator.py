#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging

from abc import ABC, abstractmethod


_LOGGER = logging.getLogger(__name__)


class RSSGenerator(ABC):
    @abstractmethod
    def authenticate(self, login, password) -> bool:
        """Authenticate to the system. Usually obtains access token or username/password pair for further use.

        Returns 'True' if succeed, otherwise False.
        """
        message = "method not implemented"
        raise NotImplementedError(message)

    @abstractmethod
    def generate(self) -> dict[str, str]:
        """Grab data and generate RSS feed.

        Returned dict keys are relative paths to files where content from value will be stored to.
        Returns None if there was problem with generator.
        """
        message = "method not implemented"
        raise NotImplementedError(message)

    # override if needed
    def close(self):
        """Request close on any open resources."""
        return
