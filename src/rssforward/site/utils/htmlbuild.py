#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging


_LOGGER = logging.getLogger(__name__)


def convert_title(title):
    return f"<!-- convert_title --><div><b>{title}</b></div>"


def convert_content(title, elements_list):
    content = " ".join(elements_list)
    if title:
        title_content = convert_title(title)
        return f"<!-- convert_content --><div>{title_content}{content}</div>\n"
    # else
    return f"<!-- convert_content -->{content}\n"


def convert_list(title, elements_list):
    content = wrap_list(elements_list, inline=False)
    if title:
        title_content = convert_title(title)
        return f"""<!-- convert_list --><div>{title_content}{content}</div>\n"""
    # else
    return f"<!-- convert_list -->{content}\n"


def convert_line(title, elements_list, inline=True):
    content = wrap_list(elements_list, inline=True)
    if title:
        title_content = convert_title(title)
        if inline:
            return f"<!-- convert_line --><div><b>{title}</b> {content}</div>\n"
        return f"<!-- convert_line --><div>{title_content}{content}</div>\n"
    # else
    return f"<!-- convert_line -->{content}"


def wrap_list(elements_list, inline=False):
    li_style = ""
    separator = " "
    if inline:
        li_style = """style="display: inline;" """
        separator = " | "
    content = ""
    content += f"""<ul style="margin: 0px"> <li {li_style}>"""
    content += f"""</li>{separator}<li {li_style}>""".join(elements_list)
    content += "</li> </ul>"
    return content
