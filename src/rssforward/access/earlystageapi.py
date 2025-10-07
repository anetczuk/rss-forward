#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import logging
import json
import requests


_LOGGER = logging.getLogger(__name__)


# 400 Bad Request
# 401 Unauthorized
# 405 Method Not Allowed


def get_auth_data(username: str, password: str):
    """Get authentication token and list of students IDs associated with the account."""
    url = "https://office-api.earlystage.pl/api/parent/auth/login"
    data = f'{{"email":"{username}","password":"{password}"}}'
    response = requests.post(url, data=data, timeout=30)

    if response.status_code != 200:
        message = f"unable to authenticate: {response.status_code}"
        raise RuntimeError(message)

    data_dict = json.loads(response.text)
    data_results = data_dict.get("results")
    data_token = data_results.get("apiToken")

    user_data = data_results.get("user")
    parent_data = user_data.get("parent")
    students_list = parent_data.get("students")

    if students_list is None:
        # it can happen that parent account does not have assigned students
        # it happens if student decided to stop attending to classes
        return data_token, None

    data_id_list = [item.get("id") for item in students_list]

    return data_token, data_id_list


def get_auth_header(token):
    return {"X-AUTH-TOKEN": token}


def get_json_data(token, url, *, throw=True):
    headers = get_auth_header(token)
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        if throw:
            message = f"unable to get data: {response.status_code}"
            raise RuntimeError(message)
        return None
    return json.loads(response.text)


def get_attendances(token, student_id):
    url = (
        f"https://office-api.earlystage.pl/api/parent/me/students/{student_id}/attendances"
        "?dateFrom=2023-09-01&dateTo=2024-08-31"
    )
    return get_json_data(token, url)


def get_homeworks(token, student_id):
    url = f"https://office-api.earlystage.pl/api/parent/me/students/{student_id}/homeworks"
    homeworks = get_json_data(token, url)

    url = f"https://office-api.earlystage.pl/api/parent/me/students/{student_id}/homeworks/incoming"
    homeworks_inc = get_json_data(token, url)

    return homeworks, homeworks_inc


def get_grades(token, student_id):
    url = (
        f"https://office-api.earlystage.pl/api/parent/me/students/{student_id}/grades"
        "?dateFrom=2023-09-01&dateTo=2024-08-31"
    )
    return get_json_data(token, url, throw=False)
