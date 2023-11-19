#!/usr/bin/python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

from rssforward import logger
from rssforward.site.librus import run


def main():
    logger.configure()
    run()
    return 0


if __name__ == "__main__":
    main()
