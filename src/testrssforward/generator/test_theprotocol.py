#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import unittest
from testrssforward.data import read_data

from rssforward.site.theprotocol import add_offer
from rssforward.rss.utils import dumps_feed_gen, init_feed_gen


class TheProtocolTest(unittest.TestCase):
    def setUp(self):
        ## Called before testfunction is executed
        pass

    def tearDown(self):
        ## Called after testfunction was executed
        pass

    def test_add_offer(self):
        feed_gen = init_feed_gen("www.google.com")
        feed_gen.title("title")
        feed_gen.description("desc")

        content = read_data("german.html")
        add_offer(feed_gen, "offer", content=content)

        # expect no exception
        dumps_feed_gen(feed_gen)
