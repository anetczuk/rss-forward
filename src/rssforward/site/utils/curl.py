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
def curl_get(session, targetUrl, params_dict=None, header_list=None):
    #     _LOGGER.info( "accessing url: %s params: %s", targetUrl, dataDict )

    dataBuffer = BytesIO()
    #     try:

    session.setopt(pycurl.POST, 0)
    if params_dict:
        session.setopt(session.URL, targetUrl + "?" + urlencode(params_dict))
    else:
        session.setopt(pycurl.URL, targetUrl)
    session.setopt(pycurl.WRITEDATA, dataBuffer)

    if header_list:
        session.setopt(pycurl.HTTPHEADER, header_list)

    session.perform()
    #         except Exception as err:
    #             _LOGGER.exception("Unexpected exception")
    #             return ""
    #     finally:
    #         session.close()
    return dataBuffer


## perform 'POST' request on curl session
def curl_post(session, targetUrl, dataDict, header_list=None, verbose=False):
    #     _LOGGER.info( "accessing url: %s params: %s", targetUrl, dataDict )

    dataBuffer = BytesIO()
    session.setopt(pycurl.URL, targetUrl)
    session.setopt(pycurl.POST, 1)
    session.setopt(pycurl.POSTFIELDS, urlencode(dataDict))
    session.setopt(pycurl.WRITEDATA, dataBuffer)

    if header_list:
        session.setopt(pycurl.HTTPHEADER, header_list)

    if verbose:
        session.setopt(pycurl.VERBOSE, 1)
    else:
        session.setopt(pycurl.VERBOSE, 0)

    session.perform()
    return dataBuffer


def curl_download(session, sourceUrl, outputFile, repeatsOnFail=0):
    repeatsOnFail = max(repeatsOnFail, 0)
    for _ in range(0, repeatsOnFail):
        try:
            curl_download_raw(session, sourceUrl, outputFile)
            ## done -- returning
            return
        except pycurl.error:
            _LOGGER.exception("could not download file")

    curl_download_raw(session, sourceUrl, outputFile)


def curl_download_raw(session, sourceUrl, outputFile):
    fd, path = tempfile.mkstemp()
    try:
        session.setopt(pycurl.URL, sourceUrl)
        session.setopt(pycurl.POST, 0)
        with os.fdopen(fd, "wb") as tmp:
            session.setopt(session.WRITEFUNCTION, tmp.write)
            session.perform()
        copyfile(path, outputFile)
    finally:
        _LOGGER.info("removing temporary file: %s", path)
        os.remove(path)
