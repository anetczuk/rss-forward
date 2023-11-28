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

from rssforward.utils import save_recent_date, get_recent_date, write_data
from rssforward.rssgenerator import RSSGenerator
from rssforward.configfile import ConfigField, ConfigKey, AuthType
from rssforward.access.keepassxcauth import get_auth_data as get_keepassxc_auth_data

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


def get_auth_data(auth_params):
    auth_type = auth_params.get(ConfigField.AUTH_TYPE.value, "RAW")
    if auth_type == AuthType.RAW.name:
        _LOGGER.info("authenticate using raw data")
        login = auth_params.get(ConfigField.AUTH_LOGIN.value)
        password = auth_params.get(ConfigField.AUTH_PASS.value)
        return (login, password)

    if auth_type == AuthType.KEEPASSXC.name:
        _LOGGER.info("authenticate using keepassxc")
        itemurl = auth_params.get(ConfigField.AUTH_ITEMURL.value)
        auth_data = get_keepassxc_auth_data(itemurl)
        login = auth_data.get("login")
        password = auth_data.get("password")
        return (login, password)

    _LOGGER.warning("unsupported authentication method: '%s'", auth_type)
    return (None, None)


#
class RSSManager:
    def __init__(self, parameters):
        self._params = parameters.copy()
        self._generators: Dict[str, RSSGenerator] = {}
        self._initializeGenerators()

    def generateData(self):
        _LOGGER.info("========== generating RSS data ==========")
        recent_datetime = get_recent_date()

        for gen_id, gen in self._generators.items():
            gen_data = gen.generate()
            self._writeData(gen_id, gen_data)

        save_recent_date(recent_datetime)
        _LOGGER.info("========== generation ended ==========")

    def _initializeGenerators(self):
        self._generators = get_generators()
        gen_id_list = list(self._generators.keys())
        scrapers_params = self._params.get(ConfigKey.SITE.value, {})
        for gen_id in gen_id_list:
            gen_params = scrapers_params.get(gen_id, {})
            if not gen_params.get(ConfigField.ENABLED.value, True):
                del self._generators[gen_id]

        # gen: RSSGenerator
        for gen_id, gen in self._generators.items():
            gen_params = scrapers_params.get(gen_id, {})
            auth_params = gen_params.get(ConfigKey.AUTH.value)
            login, password = get_auth_data(auth_params)
            gen.authenticate(login, password)

    def _writeData(self, generator_id, generator_data):
        data_root_dir = self._params.get(ConfigKey.GENERAL.value, {}).get(ConfigField.DATAROOT.value)
        for gen_item in generator_data:
            # feed_gen: FeedGenerator
            for rss_out, content in gen_item.items():
                out_dir = os.path.join(data_root_dir, generator_id)
                os.makedirs(out_dir, exist_ok=True)
                feed_path = os.path.join(out_dir, rss_out)
                _LOGGER.info("writing %s content to file: %s", generator_id, feed_path)
                write_data(feed_path, content)
