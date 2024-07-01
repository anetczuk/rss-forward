#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
import json


_LOGGER = logging.getLogger(__name__)


def extract_data_dict(soup):
    offer_json_list = soup.select('script[id="__NEXT_DATA__"]')  # all React web pages have this json embedded
    if len(offer_json_list) < 1:
        _LOGGER.warning("unable to find job offer json")
        return None

    json_content = offer_json_list[0].string
    data_dict = json.loads(json_content)
    return data_dict


def get_nested_dict(data_dict, key_list):
    sub_dict = data_dict
    for key_item in key_list:
        sub_dict = sub_dict.get(key_item)
        if sub_dict is None:
            return None
    return sub_dict
