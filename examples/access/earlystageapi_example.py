#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import contextlib

with contextlib.suppress(ImportError):
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=E0401,W0611
    # ruff: noqa: F401
    import __init__

    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded


import os
import logging
import pprint

from rssforward import TMP_DIR
from rssforward.utils import write_data
from rssforward.access.earlystageapi import get_auth_data, get_attendances, get_homeworks, get_grades
from rssforward.keepass.keepassauth import get_auth_data as get_keepasxc_auth_data


_LOGGER = logging.getLogger(__name__)


def main():
    auth_data = get_keepasxc_auth_data("https://online.earlystage.pl/logowanie/")

    username = auth_data.get("login")
    password = auth_data.get("password")

    auth_data = get_auth_data(username, password)
    token = auth_data[0]
    student_id = auth_data[1][0]

    out_dir = os.path.join(TMP_DIR, "earlystage")
    os.makedirs(out_dir, exist_ok=True)

    attendances = get_attendances(token, student_id)

    out_file = os.path.join(out_dir, "attendances.txt")
    _LOGGER.info("writing output %s", out_file)
    content = pprint.pformat(attendances)
    write_data(out_file, content)

    homeworks, homeworks_incoming = get_homeworks(token, student_id)

    out_file = os.path.join(out_dir, "homeworks.txt")
    _LOGGER.info("writing output %s", out_file)
    content = pprint.pformat(homeworks)
    write_data(out_file, content)

    out_file = os.path.join(out_dir, "homeworks_incoming.txt")
    _LOGGER.info("writing output %s", out_file)
    content = pprint.pformat(homeworks_incoming)
    write_data(out_file, content)

    grades = get_grades(token, student_id)

    out_file = os.path.join(out_dir, "grades.txt")
    _LOGGER.info("writing output %s", out_file)
    content = pprint.pformat(grades)
    write_data(out_file, content)


if __name__ == "__main__":
    main()
