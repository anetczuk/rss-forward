#!/usr/bin/env python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

try:
    ## following import success only when file is directly executed from command line
    ## otherwise will throw exception when executing as parameter for "python -m"
    # pylint: disable=W0611
    import __init__
except ImportError:
    ## when import fails then it means that the script was executed indirectly
    ## in this case __init__ is already loaded
    pass


from rssforward import logger
from rssforward.access.keepassxcauth import KeepassxcAuth
from rssforward.site.earlystage import MAIN_URL


def main():
    logger.configure()

    auth = KeepassxcAuth(client_id="xxx", state_file_path="/tmp/xxx.assoc")  # nosec
    auth.connect()

    auth_data = auth.getAuthData(MAIN_URL)
    print("unlocking done, login:", auth_data.get("login"))


if __name__ == "__main__":
    main()
