#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging

import os
import zipfile
import filecmp
import pickle


_LOGGER = logging.getLogger(__name__)


class RenamingUnpickler(pickle.Unpickler):
    def __init__(self, code_version, file):
        super().__init__(file)
        self.codeVersion = code_version

    def find_class(self, module, name):
        renamed_module = module
        if module == "rsscast.gui.datatypes":
            renamed_module = "rsscast.datatypes"
        return super().find_class(renamed_module, name)


def load_object(input_file, code_version, default_value=None):
    try:
        _LOGGER.info("loading data from: %s", input_file)
        with open(input_file, "rb") as fp:
            unpickler = RenamingUnpickler(code_version, fp)
            return unpickler.load()
    #             return pickle.load(fp)
    except FileNotFoundError:
        _LOGGER.exception("failed to load")
        return default_value
    except AttributeError:
        _LOGGER.exception("failed to load")
        return default_value
    except Exception:
        _LOGGER.exception("failed to load")
        raise


def store_object(input_object, output_file):
    tmp_file = output_file + "_tmp"
    store_object_simple(input_object, tmp_file)

    if os.path.isfile(output_file) is False:
        ## output file does not exist -- rename file
        _LOGGER.info("saving data to: %s", output_file)
        os.rename(tmp_file, output_file)
        return True

    if filecmp.cmp(tmp_file, output_file) is True:
        ## the same files -- remove tmp file
        _LOGGER.info("no new data to store in %s", output_file)
        os.remove(tmp_file)
        return False

    _LOGGER.info("saving data to: %s", output_file)
    os.remove(output_file)
    os.rename(tmp_file, output_file)
    return True


def store_backup(input_object, output_file):
    if store_object(input_object, output_file) is False:
        return False
    ## backup data
    stored_zip_file = output_file + ".zip"
    backup_files([output_file], stored_zip_file)
    return True


def load_object_simple(input_file, default_value=None, *, silent=False):
    try:
        #         _LOGGER.info( "loading data from: %s", input_file )
        with open(input_file, "rb") as fp:
            return pickle.load(fp)
    except AttributeError:
        if silent is False:
            _LOGGER.exception("failed to load: %s", input_file)
        return default_value
    except FileNotFoundError:
        if silent is False:
            _LOGGER.error("failed to load: %s", input_file)
        return default_value
    except ModuleNotFoundError:
        ## class moved to other module
        if silent is False:
            _LOGGER.exception("failed to load: %s", input_file)
        return default_value


def store_object_simple(input_object, output_file):
    outdir_dir = os.path.dirname(output_file)
    if not os.path.exists(outdir_dir):
        os.makedirs(outdir_dir, exist_ok=True)

    with open(output_file, "wb") as fp:
        pickle.dump(input_object, fp)


def backup_files(input_files, output_archive):
    ## create zip
    tmp_zip_file = output_archive + "_tmp"
    with zipfile.ZipFile(tmp_zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in input_files:
            zip_entry = os.path.basename(file)
            zipf.write(file, zip_entry)

    ## compare content
    stored_zip_file = output_archive
    if os.path.isfile(stored_zip_file) is False:
        ## output file does not exist -- rename file
        _LOGGER.info("storing data to: %s", stored_zip_file)
        os.rename(tmp_zip_file, stored_zip_file)
        return

    if filecmp.cmp(tmp_zip_file, stored_zip_file) is True:
        ## the same files -- remove tmp file
        _LOGGER.info("no new data to backup")
        os.remove(tmp_zip_file)
        return

    ## rename files
    counter = 1
    next_file = f"{stored_zip_file}.{counter}"
    while os.path.isfile(next_file):
        counter += 1
        next_file = f"{stored_zip_file}.{counter}"
    _LOGGER.info("found backup slot: %s", next_file)

    curr_file = stored_zip_file
    while counter > 1:
        curr_file = f"{stored_zip_file}.{counter - 1}"
        os.rename(curr_file, next_file)
        next_file = curr_file
        counter -= 1

    os.rename(stored_zip_file, next_file)
    os.rename(tmp_zip_file, stored_zip_file)


def compare_files_bytes(file_1_path, file_2_path):
    content_a = read_file_bytes(file_1_path)
    content_b = read_file_bytes(file_2_path)
    a_size = len(content_a)
    b_size = len(content_b)
    if a_size != b_size:
        _LOGGER.info("files size differ: %s %s", a_size, b_size)
        return
    for i in range(a_size):
        if content_a[i] != content_b[i]:
            _LOGGER.info("files differ at byte %s: %s %s", i, content_a[i], content_b[i])


def print_file_content(file_path):
    byte_list = read_file_bytes(file_path)
    # return ''.join('{:02x} '.format(x) for x in byte_list)
    b_size = len(byte_list)
    for i in range(b_size):
        # ruff: noqa: T201
        print(f"byte {i:06d}: {byte_list[i]:02x}")
        # print( ''.join( '{:06d}: {:02x}'.format( i, byte_list[i] ) ) )


def read_file_bytes(file_path):
    byte_list = []
    with open(file_path, "rb") as f:
        while 1:
            byte_s = f.read(1)
            if not byte_s:
                break
            byte_list.append(byte_s[0])
    return byte_list


## ==========================================================


class Versionable:
    def __getstate__(self):
        """Get object's state."""
        if not hasattr(self, "_class_version"):
            message = "Your class must define _class_version class variable"
            raise RuntimeError(message)
        # pylint: disable=E1101
        return {"_class_version": self._class_version, **self.__dict__}

    def __setstate__(self, dict_):
        """Restore object state."""
        version_present_in_pickle = dict_.pop("_class_version", None)
        # pylint: disable=E1101
        if version_present_in_pickle == self._class_version:  # type: ignore[attr-defined]
            # pylint: disable=W0201
            self.__dict__ = dict_
        else:
            self._convertstate_(dict_, version_present_in_pickle)

    def _convertstate_(self, dict_, dict_version_):
        # pylint: disable=E1101,C0301
        _LOGGER.info("converting object from version %s to %s", dict_version_, self._class_version)  # type: ignore[attr-defined]
        # pylint: disable=W0201
        self.__dict__ = dict_


#     @abc.abstractmethod
#     def _convertstate_(self, dict_, dict_version_ ):
#         raise NotImplementedError('You need to define this method in derived class!')
