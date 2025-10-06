#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest

import datetime
from rssforward.access.facebookscraper import pub_string_to_date


class FacebookScraperTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass

    def tearDown(self):
        ## Called after testfunction was executed
        pass

    def test_pub_string_to_date_en_date(self):
        date: datetime.datetime = pub_string_to_date("July 9")
        self.assertEqual(datetime.datetime.now(tz=datetime.timezone.utc).year, date.year)
        self.assertEqual(7, date.month)
        self.assertEqual(9, date.day)
        self.assertEqual(0, date.hour)
        self.assertEqual(0, date.minute)

    def test_pub_string_to_date_en_datetime(self):
        # ruff: noqa: RUF001
        date: datetime.datetime = pub_string_to_date("September 8 at 3:50 PM")
        self.assertEqual(datetime.datetime.now(tz=datetime.timezone.utc).year, date.year)
        self.assertEqual(9, date.month)
        self.assertEqual(8, date.day)
        self.assertEqual(15, date.hour)
        self.assertEqual(50, date.minute)
