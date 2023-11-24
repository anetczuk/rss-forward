#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from typing import List

from rssforward.utils import save_recent_date, get_recent_date
from rssforward.rssgenerator import RSSGenerator

from rssforward.site.librus import LibusGenerator
from rssforward.site.earlystage import EarlyStageGenerator


_LOGGER = logging.getLogger(__name__)


#
class RSSManager:
    def __init__(self):
        self._generators: List[RSSGenerator] = []
        self._initializeGenerators()

    def generateData(self):
        _LOGGER.info("generating RSS data")
        recent_datetime = get_recent_date()

        for gen in self._generators:
            gen.generate()

        save_recent_date(recent_datetime)

    def _initializeGenerators(self):
        self._generators.append(LibusGenerator())
        self._generators.append(EarlyStageGenerator())
