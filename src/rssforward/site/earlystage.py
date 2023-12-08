#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import logging
from typing import Dict
import datetime

from rssforward.utils import convert_to_html, string_to_date, add_timezone, calculate_dict_hash
from rssforward.rssgenerator import RSSGenerator
from rssforward.access.earlystageapi import get_auth_data, get_attendances, get_homeworks, get_grades
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen


_LOGGER = logging.getLogger(__name__)


MAIN_URL = "https://online.earlystage.pl/"


#
class EarlyStageGenerator(RSSGenerator):
    def __init__(self):
        super().__init__()
        self._token = None
        self._student_id = None

    def authenticate(self, login, password):
        auth_data = get_auth_data(login, password)
        self._token = auth_data[0]
        self._student_id = auth_data[1][0]

    def generate(self) -> Dict[str, str]:
        _LOGGER.info("========== running earlystage scraper ==========")

        if not self._token:
            _LOGGER.warning("unable to generate content, because generator is not authenticated")
            return {}

        ret_dict: Dict[str, str] = {}

        _LOGGER.info("accessing attendances")
        attendances = get_attendances(self._token, self._student_id)
        gen_data = generate_attendances_feed(attendances)
        ret_dict.update(gen_data)

        _LOGGER.info("accessing homeworks")
        homeworks, incoming = get_homeworks(self._token, self._student_id)
        gen_data = generate_homeworks_feed(homeworks, incoming)
        ret_dict.update(gen_data)

        _LOGGER.info("accessing homeworks")
        grades = get_grades(self._token, self._student_id)
        gen_data = generate_grades_feed(grades)
        ret_dict.update(gen_data)

        return ret_dict


# ============================================


ATTEND_STATUS_DICT = {
    # 0: "spóźnienie",
    1: "obecny"
    # 2: "nieobecny",
    # 3: "brak książki"
}


def generate_attendances_feed(attendances):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Obecności")
    feed_gen.description("obecności")

    att_list = attendances.get("results", [])
    for item in att_list:
        # pprint.pprint(item)
        lesson = item.get("lesson", {})
        lesson_name = lesson.get("name")
        lesson_date = lesson.get("date")
        lesson_subject = lesson.get("subject")
        attend_status = item.get("status")
        status_label = ATTEND_STATUS_DICT.get(attend_status, attend_status)

        data_dict = {"item_date": lesson_date, "name": lesson_name, "subject": lesson_subject, "status": status_label}
        add_atendence(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"attendance.xml": content}


def add_atendence(feed_gen, data_dict):
    lesson_date = data_dict["item_date"]
    lesson_name = data_dict["name"]
    lesson_subject = data_dict["subject"]
    status_label = data_dict["status"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{lesson_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"Obecność w dniu {lesson_date}: {status_label}")
    feed_item.author({"name": "earlystage", "email": "earlystage"})

    # fill description
    item_desc = f"""\
Lekcja: {lesson_name}
Temat lekcji: {lesson_subject}
Data: {lesson_date}
Obecność: {status_label}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(lesson_date)
    feed_item.pubDate(item_date)


HW_STATUS_DICT = {0: "Niesprawdzona", 1: "Odrobione", 2: "Częsciowo odrobione", 3: "<b>Nieodrobione</b>"}


def generate_homeworks_feed(homework, incoming):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Prace domowe")
    feed_gen.description("prace domowe")

    hw_list = homework.get("results", [])
    for item in hw_list:
        # pprint.pprint(item)
        lesson = item.get("lesson", {})
        homework_subject = lesson.get("homeworkSubject")
        if not homework_subject:
            # no homework to do - skip
            continue
        lesson_date = lesson.get("date")
        lesson_subject = lesson.get("subject")
        homework_checked = lesson.get("homeworkChecked")
        homework_status = item.get("status")

        data_dict = {
            "item_date": lesson_date,
            "lesson_subject": lesson_subject,
            "homework_subject": homework_subject,
            "checked": homework_checked,
            "status": homework_status,
        }
        add_homework(feed_gen, data_dict)

    hw_list = incoming.get("results", [])
    for item in hw_list:
        # pprint.pprint(item)
        homework_subject = item.get("homeworkSubject")
        if not homework_subject:
            # no homework to do - skip
            continue
        homework_date = item.get("date")

        data_dict = {"item_date": homework_date, "subject": homework_subject}
        add_homework_incoming(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"homework.xml": content}


def add_homework(feed_gen, data_dict):
    lesson_date = data_dict["item_date"]
    lesson_subject = data_dict["lesson_subject"]
    homework_subject = data_dict["homework_subject"]
    homework_checked = data_dict["checked"]
    homework_status = data_dict["status"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{lesson_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"Status pracy domowej na {lesson_date}: {homework_subject}")
    feed_item.author({"name": "earlystage", "email": "earlystage"})

    # fill description
    status_label = HW_STATUS_DICT.get(homework_status, homework_status)

    item_desc = f"""\
Zadanie: {homework_subject}
Temat lekcji: {lesson_subject}
Na kiedy: {lesson_date}
Czy praca sprawdzona: {homework_checked}
Status: {status_label}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(lesson_date)
    feed_item.pubDate(item_date)


def add_homework_incoming(feed_gen, data_dict):
    homework_date = data_dict["item_date"]
    homework_subject = data_dict["subject"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{homework_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"Nowa praca domowa na {homework_date}: {homework_subject}")
    feed_item.author({"name": "earlystage", "email": "earlystage"})
    # fill description

    item_desc = f"""\
Zadanie: {homework_subject}
Na kiedy: {homework_date}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(homework_date)
    feed_item.pubDate(item_date)


GRADE_DESC_DICT = {
    "^": "Dziecko robi wyraźny postęp (nawet jeśli pojawiło się kilka błędów, pamiętajmy,"
    " że w procesie uczenia się, popełnianie błędów jest jego częścią).",
    "@": "Dziecko robi postępy, jednak, aby jeszcze lepiej potrenować daną umiejętność, zalecamy dalsze ćwiczenia.",
}


def get_grade_meaning(grade, grade_perc):
    grade_meaning = GRADE_DESC_DICT.get(grade)
    if grade_meaning:
        return grade_meaning
    if grade_perc is None:
        return None
    if grade_perc >= 0.8:
        return "80-100% - opanowanie materiału zgodnie z założeniami (a nawet powyżej)!"
    if grade_perc >= 0.7:
        return (
            "70-80% - opanowanie większości materiału zgodnie z założeniami,"
            " ale dobrze jest cały czas pilnować systematycznej nauki"
        )
    if grade_perc >= 0.5:
        return (
            "50-70% - opanowanie dużej ilości zagadnień zgodnie z założeniami;"
            " w niektórych obszarach potrzebna jest jednak dalsza praca i wzmożenie wysiłku"
        )
    return "konieczność przystąpienia do testu, kartkówki lub egzaminu ponownie"


def generate_grades_feed(grades):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Oceny")
    feed_gen.description("oceny")

    grades_list = grades.get("results", [])
    for item in grades_list:
        # pprint.pprint(item)
        grade_desc = item.get("gradeDescription", {})
        description = grade_desc.get("description")
        grade_type = grade_desc.get("gradeCategory", {}).get("namePl")
        month = grade_desc.get("month")
        year = grade_desc.get("year")
        # grade_month = grade_desc.get("lesson", {}).get("date")
        grade_date = datetime.datetime(year=year, month=month, day=1).date()
        grade_date_str = grade_date.strftime("%Y-%m-%d")

        grade_datetime = datetime.datetime(year=year, month=month, day=1)
        grade_datetime = add_timezone(grade_datetime)
        grade = item.get("grades", {}).get("_gradeFormat")
        grade_points = item.get("points")
        grade_points_max = item.get("pointsMax")
        grade_perc = None
        if grade_points is not None and grade_points_max is not None:
            grade_perc = grade_points / grade_points_max
        grade_meaning = get_grade_meaning(grade, grade_perc)

        data_dict = {
            "item_date": grade_date_str,
            "type": grade_type,
            "grade": grade,
            "description": description,
            "meaning": grade_meaning,
        }
        add_grade(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"grade.xml": content}


def add_grade(feed_gen, data_dict):
    grade_date = data_dict["item_date"]
    grade_type = data_dict["type"]
    grade = data_dict["grade"]
    description = data_dict["description"]
    grade_meaning = data_dict["meaning"]

    grade_datetime = string_to_date(grade_date)
    grade_month = grade_datetime.month

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{grade_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
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


# ============================================================


def get_generator() -> RSSGenerator:
    return EarlyStageGenerator()
