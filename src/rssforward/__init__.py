#!/usr/bin/python3
#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TMP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir, "tmp"))
DATA_DIR = os.path.abspath(os.path.join(TMP_DIR, "data"))
