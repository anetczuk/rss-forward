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
    def generate(self):
        raise NotImplementedError("method not implemented")
