#
# Copyright (c) 2024, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import os
import tempfile
from shutil import copyfile
import logging
from io import BytesIO

from urllib.parse import urlencode

import pycurl


_LOGGER = logging.getLogger(__name__)


def get_curl_session(user_agent=None):
    session = pycurl.Curl()
    if user_agent is None:
        user_agent = "curl/7.58.0"
    session.setopt(pycurl.USERAGENT, user_agent)
    # ruff: noqa: FBT003
    session.setopt(pycurl.FOLLOWLOCATION, True)  ## follow redirects
    session.setopt(pycurl.CONNECTTIMEOUT, 60)  ## connection phase timeout
    #         session.setopt( pycurl.TIMEOUT, 60 )                 ## whole request timeout (transfer?)
    #         c.setopt( c.VERBOSE, 1 )
    session.setopt(pycurl.COOKIEJAR, "/tmp/cookie.txt")  ## save cookies to a file
    session.setopt(pycurl.COOKIEFILE, "/tmp/cookie.txt")  ## load cookies from a file
    return session


def get_status_code(session):
    return session.getinfo(pycurl.HTTP_CODE)


## perform 'GET' request on curl session
def curl_get(session, target_url, params_dict=None, header_list=None):
    #     _LOGGER.info( "accessing url: %s params: %s", target_url, dataDict )

    data_buffer = BytesIO()
    #     try:

    session.setopt(pycurl.POST, 0)  ## disable POST
    if params_dict:
        session.setopt(session.URL, target_url + "?" + urlencode(params_dict))
    else:
        session.setopt(pycurl.URL, target_url)
    session.setopt(pycurl.WRITEDATA, data_buffer)

    if header_list:
        session.setopt(pycurl.HTTPHEADER, header_list)

    session.perform()
    #         except Exception as err:
    #             _LOGGER.exception("Unexpected exception")
    #             return ""
    #     finally:
    #         session.close()
    return data_buffer


def curl_get_content(url, session=None):
    if session is None:
        session = get_curl_session("Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0")
    response = curl_get(session, url)
    response_code = get_status_code(session)
    if response_code not in (200, 204):
        _LOGGER.warning("unable to get content, code: %s url: %s", response_code, url)
        return None

    response_text: str = response.getvalue().decode("utf-8")
    return response_text


## perform 'POST' request on curl session
def curl_post(session, target_url, data_dict, header_list=None, *, verbose=False):
    #     _LOGGER.info( "accessing url: %s params: %s", target_url, data_dict )

    data_buffer = BytesIO()
    session.setopt(pycurl.URL, target_url)
    session.setopt(pycurl.POST, 1)
    session.setopt(pycurl.POSTFIELDS, urlencode(data_dict))
    session.setopt(pycurl.WRITEDATA, data_buffer)

    if header_list:
        session.setopt(pycurl.HTTPHEADER, header_list)

    if verbose:
        session.setopt(pycurl.VERBOSE, 1)
    else:
        session.setopt(pycurl.VERBOSE, 0)

    session.perform()
    return data_buffer


def curl_download(session, source_url, output_file, repeats_on_fail=0):
    repeats_on_fail = max(repeats_on_fail, 0)
    for _i in range(repeats_on_fail):
        try:
            curl_download_raw(session, source_url, output_file)

        # ruff: noqa: PERF203
        except pycurl.error:
            _LOGGER.exception("could not download file")

        else:
            ## done -- returning
            return

    curl_download_raw(session, source_url, output_file)


def curl_download_raw(session, source_url, output_file):
    fd, path = tempfile.mkstemp()
    try:
        session.setopt(pycurl.URL, source_url)
        session.setopt(pycurl.POST, 0)
        with os.fdopen(fd, "wb") as tmp:
            session.setopt(session.WRITEFUNCTION, tmp.write)
            session.perform()
        copyfile(path, output_file)
    finally:
        _LOGGER.info("removing temporary file: %s", path)
        os.remove(path)
