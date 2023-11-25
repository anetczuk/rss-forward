#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import logging
from typing import Dict

import pkgutil

from rssforward.utils import save_recent_date, get_recent_date
from rssforward.rssgenerator import RSSGenerator

import rssforward.site


_LOGGER = logging.getLogger(__name__)


# returns list of instances of base generator class
def get_generators() -> Dict[str, RSSGenerator]:
    ret_data = {}

    generators_module = rssforward.site
    generators_path = os.path.dirname(generators_module.__file__)

    modules_list = pkgutil.iter_modules([generators_path])
    for mod_info in modules_list:
        mod_name = mod_info.name
        mod_full_name = f"{generators_module.__name__}.{mod_name}"
        mod = __import__(mod_full_name, fromlist=[""])
        try:
            generator = mod.get_generator()
            ret_data[mod_name] = generator
            _LOGGER.info("loaded generator from module %s", mod_full_name)
        except AttributeError as exc:
            _LOGGER.warning("unable to load generator from module %s, reason: %s", mod_full_name, exc)

    return ret_data


#
class RSSManager:
    def __init__(self):
        self._generators: Dict[str, RSSGenerator] = {}
        self._initializeGenerators()

    def generateData(self):
        _LOGGER.info("generating RSS data")
        recent_datetime = get_recent_date()

        for gen in self._generators.values():
            gen.generate()

        save_recent_date(recent_datetime)

    def _initializeGenerators(self):
        self._generators = get_generators()
        for gen in self._generators.values():
            gen.authenticate()
