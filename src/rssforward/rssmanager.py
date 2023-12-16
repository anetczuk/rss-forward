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
import threading

import pkgutil

from rssforward.utils import save_recent_date, get_recent_date, write_data
from rssforward.rssgenerator import RSSGenerator
from rssforward.configfile import ConfigField, ConfigKey, AuthType
from rssforward.access.keepassxcauth import get_auth_data as get_keepassxc_auth_data, close as keepassxc_close

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
    class State:
        """Container for generator and it's state."""

        def __init__(self, generator: RSSGenerator = None):
            self.generator: RSSGenerator = generator
            self.valid = True  # is problem with generator?

    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        self._params = parameters.copy()
        self._generators: Dict[str, RSSManager.State] = None

    def isGenValid(self):
        """Check if all generators are valid.

        Return 'True' if valid, otherwise 'False'.
        """
        if not self._generators:
            # not initialized
            return False
        for gen_id, gen_state in self._generators.items():
            if not gen_state.valid:
                _LOGGER.info("invalid generator: %s", gen_id)
                return False
        # everything ok
        return True

    # returns 'True' if everything is OK, otherwise 'False'
    def generateData(self):
        if self._generators is None:
            self._initializeGenerators()
        if not self._generators:
            return

        _LOGGER.info("========== generating RSS data ==========")
        recent_datetime = get_recent_date()

        for gen_id, gen_state in self._generators.items():
            gen = gen_state.generator
            gen_data: Dict[str, str] = gen.generate()
            if not gen_data:
                _LOGGER.info("generatorion not completed for generator %s", gen_id)
                gen_state.valid = False
            else:
                gen_state.valid = True
            self._writeData(gen_id, gen_data)

        save_recent_date(recent_datetime)
        _LOGGER.info("========== generation ended ==========")

    def close(self):
        for gen_state in self._generators.values():
            gen = gen_state.generator
            gen.close()
        keepassxc_close()

    def _initializeGenerators(self):
        gen_list = get_generators()
        self._generators = {}
        for gen_id, gen in gen_list.items():
            self._generators[gen_id] = RSSManager.State(gen)

        gen_id_list = list(self._generators.keys())
        scrapers_params = self._params.get(ConfigKey.SITE.value, {})
        for gen_id in gen_id_list:
            gen_params = scrapers_params.get(gen_id, {})
            if not gen_params.get(ConfigField.ENABLED.value, True):
                del self._generators[gen_id]

            # try authenticate
            gen_state = self._generators[gen_id]
            gen: RSSGenerator = gen_state.generator
            auth_params = gen_params.get(ConfigKey.AUTH.value, {})
            try:
                login, password = get_auth_data(auth_params)
                gen_state.valid = gen.authenticate(login, password)
            except Exception as exc:  # pylint: disable=W0703
                _LOGGER.warning("error during authentication of %s: %s", gen_id, exc)
                # unable to authenticate - will not be possible to generate content, so remove the generator
                del self._generators[gen_id]

    def _writeData(self, generator_id, generator_data: Dict[str, str]):
        if not generator_data:
            return
        data_root_dir = self._params.get(ConfigKey.GENERAL.value, {}).get(ConfigField.DATAROOT.value)
        for rss_out, content in generator_data.items():
            out_dir = os.path.join(data_root_dir, generator_id)
            os.makedirs(out_dir, exist_ok=True)
            feed_path = os.path.join(out_dir, rss_out)
            _LOGGER.info("writing %s content to file: %s", generator_id, feed_path)
            write_data(feed_path, content)


#
class ThreadedRSSManager:
    def __init__(self, manager):
        self._manager = manager
        self._execute_loop = False  # flag to stop thread loop
        self._state_callback = None
        self._lock = threading.RLock()
        self._wait_object = threading.Condition()
        self._thread = None

    def setStateCallback(self, callback):
        self._state_callback = callback

    def start(self, refresh_time, startupdelay):
        """Start thread."""
        with self._lock:
            if self._execute_loop:
                _LOGGER.warning("thread already running")
                return
            self._execute_loop = True
            self._thread = threading.Thread(target=self._runLoop, args=[refresh_time, startupdelay])
            _LOGGER.warning("starting thread")
            self._thread.start()

    def stop(self):
        with self._lock:
            if not self._execute_loop:
                _LOGGER.warning("thread already stopped")
                return
            _LOGGER.info("stopping thread")
            self._execute_loop = False
            try:
                with self._wait_object:
                    self._wait_object.notifyAll()
            except RuntimeError:
                # no threads wait for notification
                _LOGGER.info("thread does not wait")

    def executeLoop(self, refresh_time, startupdelay):
        """Start run loop without additional threads."""
        with self._lock:
            self._execute_loop = True
        self._runLoop(refresh_time, startupdelay)

    def executeSingle(self):
        """Trigger single generation."""
        with self._lock:
            if not self._thread:
                self._callGen()
                return

            try:
                with self._wait_object:
                    self._wait_object.notifyAll()
            except RuntimeError:
                # no threads wait for notification
                _LOGGER.info("thread does not wait")

    def _runLoop(self, refresh_time, startupdelay):
        try:
            if startupdelay > 0:
                _LOGGER.info("waiting %s seconds (startup delay)", startupdelay)
                with self._wait_object:
                    self._wait_object.wait(startupdelay)

            while True:
                with self._lock:
                    if not self._execute_loop:
                        break

                self._callGen()

                with self._wait_object:
                    with self._lock:
                        if not self._execute_loop:
                            break
                    _LOGGER.info("waiting %s seconds before next fetch", refresh_time)
                    self._wait_object.wait(refresh_time)

            _LOGGER.info("thread loop ended")
            return

        except KeyboardInterrupt:
            _LOGGER.error("keyboard interrupt")
            # executed in case of exception
            raise

        except BaseException as exc:
            _LOGGER.error("exception occurred in thread loop: %s", exc)
            # executed in case of exception
            raise

        finally:
            with self._lock:
                self._execute_loop = False

    def _callGen(self):
        if self._state_callback:
            self._state_callback(False)

        self._manager.generateData()

        if self._state_callback:
            valid = self._manager.isGenValid()
            self._state_callback(valid)

    def join(self):
        with self._lock:
            if not self._thread:
                return
            _LOGGER.info("joining thread")
        self._thread.join()
        with self._lock:
            self._thread = None
        _LOGGER.info("thread terminated")
