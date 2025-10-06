#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import contextlib

with contextlib.suppress(ImportError):
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=E0401,W0611
    # ruff: noqa: F401
    import __init__

    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded


from rssforward import logger
from rssforward.site.librus import get_generator
from rssforward.rssmanager import get_auth_data


def main():
    logger.configure()

    auth_params = {"type": "KEEPASSXC", "itemurl": "https://portal.librus.pl/rodzina/synergia/loguj"}
    login, password = get_auth_data(auth_params)

    generator = get_generator()
    generator.authenticate(login, password)
    generator.generate()


if __name__ == "__main__":
    main()
