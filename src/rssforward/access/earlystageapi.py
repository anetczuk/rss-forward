#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import json
import requests


# 400 Bad Request
# 401 Unauthorized
# 405 Method Not Allowed


def get_auth_data(username: str, password: str):
    """Get authentication token and list of students IDs associated with the account."""
    url = "https://office-api.earlystage.pl/api/parent/auth/login"
    data = f'{{"email":"{username}","password":"{password}"}}'
    response = requests.post(url, data=data, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"unable to authenticate: {response.status_code}")

    data_dict = json.loads(response.text)
    data_results = data_dict.get("results")
    data_token = data_results.get("apiToken")

    students_list = data_results.get("user").get("parent").get("students")
    data_id_list = [item.get("id") for item in students_list]

    return data_token, data_id_list


def get_auth_header(token):
    headers = {"X-AUTH-TOKEN": token}
    return headers


def get_json_data(token, url):
    headers = get_auth_header(token)
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"unable to get data: {response.status_code}")
    data = json.loads(response.text)
    return data


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
    return get_json_data(token, url)
