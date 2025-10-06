#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

from rssforward.utils import normalize_string, get_recent_date


class UtilsTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass

    def tearDown(self):
        ## Called after testfunction was executed
        pass

    def test_normalize_string_control_char(self):
        string = ["aaa\x02bbb\nccc"]
        converted = []
        converted.append(normalize_string(string[0]))
        self.assertEqual(["aaa bbb\nccc"], converted)

    def test_get_recent_date(self):
        recent = get_recent_date()
        tzinfo = recent.tzinfo
        self.assertTrue(tzinfo is not None)
