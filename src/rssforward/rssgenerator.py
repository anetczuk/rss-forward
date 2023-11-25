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


#
class RSSGenerator(ABC):
    @abstractmethod
    def authenticate(self):
        """Authenticate to the system. Usually obtains access token or username/password pair for further use."""
        raise NotImplementedError("method not implemented")

    @abstractmethod
    def generate(self):
        """Grab data and generate RSS feed."""
        raise NotImplementedError("method not implemented")
