#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

import logging
from typing import Dict
import json

from rssforward.utils import (
    convert_to_html,
    string_to_date,
    calculate_dict_hash,
    string_to_date_general,
    string_to_datetime_hm,
)
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen
from rssforward.site.utils.curl import get_curl_session, curl_post, curl_get, get_status_code


_LOGGER = logging.getLogger(__name__)


MAIN_URL = "https://simonsays.langlion.com/"


#
class SimonSaysGenerator(RSSGenerator):
    def __init__(self):
        super().__init__()
        self._session = None
        self._token = None
        self._auth_header_list = []

    def authenticate(self, login, password):
        self._session = get_curl_session(
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0"
        )

        url = "https://simonsays.langlion.com/user/checkUser"
        data = {"referer": "1", "login": login, "password": password}
        response = curl_post(self._session, url, data, header_list=[])
        response_code = get_status_code(self._session)
        if response_code != 200:
            _LOGGER.error("unable to get response, code: %s", response_code)
            return False

        text_output: str = response.getvalue().decode("utf-8")

        ## line with access token:
        ## localStorage.setItem('student_access_token', '...');
        access_token_field_index = text_output.find("student_access_token")
        if access_token_field_index < 0:
            _LOGGER.error("unable to find access token")
            return False
        access_token_field_start_index = text_output.find(" ", access_token_field_index)
        if access_token_field_start_index < 0:
            _LOGGER.error("unable to find access token")
            return False
        access_token_field_start_index += 2

        access_token_field_end_index = text_output.find(");", access_token_field_start_index)
        if access_token_field_end_index < 0:
            _LOGGER.error("unable to find access token")
            return False
        access_token_field_end_index -= 1

        self._token = text_output[access_token_field_start_index:access_token_field_end_index]
        return True

    def generate(self) -> Dict[str, str]:
        _LOGGER.info("========== running simonsays scraper ==========")

        if not self._token:
            _LOGGER.error("unable to get access token")
            return None

        self._auth_header_list = [f"Authorization: Bearer {self._token}", "Type: application/json"]

        user_id = self._getStudentId()
        if user_id is None:
            _LOGGER.error("unable to user id")
            return None

        ret_dict: Dict[str, str] = {}

        ## nothing interesting - just list of summaries
        # url = "https://simonsays.langlion.com/api/wall"

        _LOGGER.info("accessing messages")
        messages_data = self._getMessages()
        if messages_data is None:
            return None
        gen_data = generate_messages_feed(messages_data)
        ret_dict.update(gen_data)

        _LOGGER.info("accessing marks")
        marks_data = self._getMarks(user_id)
        if marks_data is None:
            return None
        gen_data = generate_marks_feed(marks_data)
        ret_dict.update(gen_data)

        _LOGGER.info("accessing documents")
        docs_data = self._getDocuments(user_id)
        if docs_data is None:
            return None
        gen_data = generate_documents_feed(docs_data)
        ret_dict.update(gen_data)

        _LOGGER.info("accessing classes")
        classes_data = self._getClasses(user_id)
        if classes_data is None:
            return None
        gen_data = generate_classes_feed(classes_data)
        ret_dict.update(gen_data)

        return ret_dict

    def _getStudentId(self):
        url = "https://simonsays.langlion.com/api/appData"
        response = curl_get(self._session, url, header_list=self._auth_header_list)
        response_code = get_status_code(self._session)
        if response_code != 200:
            _LOGGER.error("unable to get response, code: %s", response_code)
            return None
        response_output = response.getvalue()
        response_dict = json.loads(response_output)

        linked_users = response_dict.get("data", {}).get("linkedUsers", [])
        if linked_users:
            return linked_users[0].get("id")
        return None

    def _getMessages(self):
        url = "https://simonsays.langlion.com//api/messages"
        params_dict = {"mailbox": "inbox"}
        data_dict = self._fetchDataDict(url, params_dict)
        if data_dict is None:
            return None

        ret_list = []

        items_list = data_dict.get("data", {}).get("messages", {})
        for msg_data in items_list:
            msg_id = msg_data.get("id")
            if msg_id is None:
                _LOGGER.error("message id not found")
                return None

            url = "https://simonsays.langlion.com//api/message"
            params_dict = {"id": msg_id}
            message_details_data = self._fetchDataDict(url, params_dict)
            if message_details_data is None:
                return None

            message_details_data = message_details_data.get("data")
            if message_details_data is None:
                _LOGGER.error("message data not found")
                return None

            ret_list.append(message_details_data)

        return ret_list

    def _getMarks(self, student_id):
        url = "https://simonsays.langlion.com//api/marks"
        params_dict = {"student_user_id": student_id}
        data_dict = self._fetchDataDict(url, params_dict)
        if data_dict is None:
            return None

        # print("data:", json.dumps(data_dict, indent=4))

        ret_list = []

        items_list = data_dict.get("data", [])
        for data_item in items_list:
            marks = data_item.get("marks")
            if marks:
                _LOGGER.error("unhandled case - found marks!!!")
                return None

            special_marks = data_item.get("available_special_marks")
            if special_marks:
                _LOGGER.error("unhandled case - found special marks!!!")
                return None

            # ret_list.append(message_details_data)

        return ret_list

    def _getDocuments(self, student_id):
        url = "https://simonsays.langlion.com//api/student/userDocuments"
        params_dict = {"student_user_id": student_id}
        data_dict = self._fetchDataDict(url, params_dict)
        if data_dict is None:
            return None

        # print("data:", json.dumps(data_dict, indent=4))

        ret_list = []

        items_list = data_dict.get("data", {}).get("userDocuments", [])
        for data_item in items_list:
            ret_list.append(data_item)

        return ret_list

    def _getClasses(self, student_id):
        url = "https://simonsays.langlion.com//api/student/classes"
        params_dict = {"student_user_id": student_id}
        data_dict = self._fetchDataDict(url, params_dict)
        if data_dict is None:
            return None

        # print("data:", json.dumps(data_dict, indent=4))

        ret_list = []

        items_list = data_dict.get("data", {}).get("classes", [])
        for data_item in items_list:
            class_id = data_item["id"]
            url = "https://simonsays.langlion.com//api/lessonDetails"
            params_dict = {"lesson_id": class_id, "student_user_id": student_id}
            lesson_dict = self._fetchDataDict(url, params_dict)
            if lesson_dict is None:
                return None

            if lesson_dict.get("cancelStatus") is not None:
                _LOGGER.error("unhandled field 'cancelStatus' appeared")

            # print("data:", json.dumps(lesson_dict, indent=4))

            lesson_details = lesson_dict["data"]["details"]

            lesson_data = {
                "info": data_item,
                "comment": lesson_details,
            }

            ret_list.append(lesson_data)

        return ret_list

    def _fetchDataDict(self, url, params_dict=None):
        response = curl_get(self._session, url, params_dict, header_list=self._auth_header_list)
        response_code = get_status_code(self._session)
        if response_code != 200:
            _LOGGER.error("unable to get response from %s, code: %s", url, response_code)
            return None
        response_output = response.getvalue()
        return json.loads(response_output)


# ============================================


def generate_messages_feed(messages_list) -> Dict[str, str]:
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Wiadomości")
    feed_gen.description("wiadomości")

    for msg_data in messages_list:
        add_message(feed_gen, msg_data)

    content = dumps_feed_gen(feed_gen)
    return {"messages.xml": content}


def add_message(feed_gen, data_dict):
    msg_id = data_dict["id"]
    subject = data_dict["subject"]
    content = data_dict["content"]
    sender = data_dict["sender"]
    date_string = data_dict["date"]  # example: 2024-10-06 14:10:31
    attachments = data_dict["attachments"]
    have_attachments = len(attachments) > 0
    if have_attachments:
        have_attachments = "Wiadomość posiada załączniki<br/>"
    else:
        have_attachments = "<!-- no attachments -->"

    item_datetime = string_to_date_general(date_string)

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"simonsays-message-{msg_id}-{data_hash}"
    feed_item.id(item_id)

    feed_item.title(f"Wiadomość: {subject}")
    feed_item.author({"name": f"{sender}", "email": f"{sender}"})

    # fill description
    item_desc = f"""\
{have_attachments}
Treść:
<div style="margin-left: 24px">
{content}
</div>
"""
    feed_item.content(item_desc)
    # fill publish date
    feed_item.pubDate(item_datetime)


def generate_marks_feed(marks_list) -> Dict[str, str]:
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Oceny")
    feed_gen.description("oceny")

    if marks_list:
        _LOGGER.error("unhandled case - marks")

    # grades_list = grades.get("results", [])
    # for item in grades_list:
    #     # pprint.pprint(item)
    #     grade_desc = item.get("gradeDescription", {})
    #     description = grade_desc.get("description")
    #     grade_type = grade_desc.get("gradeCategory", {}).get("namePl")
    #     month = grade_desc.get("month")
    #     year = grade_desc.get("year")
    #     # grade_month = grade_desc.get("lesson", {}).get("date")
    #     grade_date = datetime.datetime(year=year, month=month, day=1).date()
    #     grade_date_str = grade_date.strftime("%Y-%m-%d")
    #
    #     grade_datetime = datetime.datetime(year=year, month=month, day=1)
    #     grade_datetime = add_timezone(grade_datetime)
    #     grade = item.get("grades", {}).get("_gradeFormat")
    #     grade_points = item.get("points")
    #     grade_points_max = item.get("pointsMax")
    #     grade_perc = None
    #     if grade_points is not None and grade_points_max is not None:
    #         grade_perc = grade_points / grade_points_max
    #     grade_meaning = get_grade_meaning(grade, grade_perc)
    #
    #     data_dict = {
    #         "item_date": grade_date_str,
    #         "type": grade_type,
    #         "grade": grade,
    #         "description": description,
    #         "meaning": grade_meaning,
    #     }
    #     add_mark(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"grades.xml": content}


def add_mark(feed_gen, data_dict):
    grade_date = data_dict["item_date"]
    grade_type = data_dict["type"]
    grade = data_dict["grade"]
    description = data_dict["description"]
    grade_meaning = data_dict["meaning"]

    grade_datetime = string_to_date(grade_date)
    grade_month = grade_datetime.month

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = (
        f"simonsays-grade-{grade_date}-{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    )
    feed_item.id(item_id)

    feed_item.title(f"Nowa ocena w miesiącu {grade_month}: {grade_type} {grade}")
    feed_item.author({"name": "earlystage", "email": "earlystage"})

    # fill description
    item_desc = f"""\
Typ: {grade_type}
Opis: {description}
Miesiąc: {grade_month}
Ocena: {grade}
Objaśnienie: {grade_meaning}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    feed_item.pubDate(grade_datetime)


def generate_documents_feed(documents_list) -> Dict[str, str]:
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Dokumenty")
    feed_gen.description("dokumenty")

    for doc_item in documents_list:
        # pprint.pprint(item)
        doc_id = doc_item.get("id")
        title = doc_item.get("title")
        description = doc_item.get("description")
        content = doc_item.get("content")
        create_date = doc_item.get("createdAt")  # example: 2024-09-12 13:21:20
        # update_date = doc_item.get("updatedAt")     # example: 2024-09-12 13:21:20

        # update_date = update_date.replace(" ", "_")
        # update_date = update_date.replace(":", "-")

        data_dict = {
            "id": f"{doc_id}",
            "title": title,
            "description": description,
            "content": content,
            "create_date": create_date,
        }
        add_document(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"documents.xml": content}


def add_document(feed_gen, data_dict):
    doc_id = data_dict["id"]
    title = data_dict["title"]
    description = data_dict["description"]
    content = data_dict["content"]
    create_date = data_dict["create_date"]
    create_date = string_to_date_general(create_date)

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"simonsays-document-{doc_id}-{data_hash}"
    feed_item.id(item_id)

    feed_item.title(f"Dokument: {title}")
    feed_item.author({"name": "simonsays", "email": "simonsays"})

    # fill description
    item_desc = f"""\
Opis: {description}<br/>
Treść:<br/>
{content}
"""
    feed_item.content(item_desc)
    # fill publish date
    feed_item.pubDate(create_date)


def generate_classes_feed(classes_list) -> Dict[str, str]:
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Zajęcia")
    feed_gen.description("zajęcia")

    for class_item in classes_list:
        # pprint.pprint(item)
        class_info = class_item["info"]
        class_details = class_item["comment"]
        class_description = ""
        for detail in class_details:
            detail_title = detail["type"]
            detail_content = detail["content"]
            class_description += f"<p>{detail_title}</p>\n"
            class_description += detail_content

        class_id = class_info.get("id")
        class_name = class_info.get("name")
        class_group = class_info.get("group")
        create_date = class_info.get("date") + " " + class_info.get("time")  # example: 2024-09-12 13:21
        class_teacher = class_info.get("teacher", [])
        class_teacher = " | ".join(class_teacher)

        details_dict = class_info.get("details", {})

        data_dict = {
            "id": class_id,
            "name": class_name,
            "group": class_group,
            "date": create_date,
            "teacher": class_teacher,
            "description": class_description,
            "details": details_dict,
        }
        add_class(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"classes.xml": content}


def add_class(feed_gen, data_dict):
    class_id = data_dict["id"]
    class_name = data_dict["name"]
    class_group = data_dict["group"]
    class_date_str = data_dict["date"]
    class_date = string_to_datetime_hm(class_date_str)
    class_teacher = data_dict["teacher"]
    description = data_dict["description"]
    details_dict = data_dict["details"]
    details = json.dumps(details_dict, indent=4)

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"simonsays-class-{class_id}-{data_hash}"
    feed_item.id(item_id)

    feed_item.title(f"Lekcja: {class_name} {class_date_str}")
    feed_item.author({"name": "simonsays", "email": "simonsays"})

    # fill description
    item_desc = f"""\
Lekcja: {class_name}<br/>
Grupa: {class_group}<br/>
Data: {class_date_str}<br/>
Nauczyciel: {class_teacher}<br/>
Status:<br/>
    <div style="margin-left: 24px">
    <pre>
{details}
    </pre>
    </div>
Opis:<br/>
    <div style="margin-left: 24px">
{description}
    </div>
"""
    feed_item.content(item_desc)
    # fill publish date
    feed_item.pubDate(class_date)


# ============================================================


def get_generator(_gen_params=None) -> RSSGenerator:
    return SimonSaysGenerator()
