#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import logging
import datetime

from rssforward.utils import convert_to_html, string_to_date, add_timezone
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

    def generate(self):
        _LOGGER.info("========== running earlystage scraper ==========")

        if not self._token:
            _LOGGER.warning("unable to generate content, because generator is not authenticated")
            return []

        ret_list = []

        _LOGGER.info("accessing attendances")
        attendances = get_attendances(self._token, self._student_id)
        gen_data = generate_attendances_feed(attendances)
        ret_list.append(gen_data)

        _LOGGER.info("accessing homeworks")
        homeworks, incoming = get_homeworks(self._token, self._student_id)
        gen_data = generate_homeworks_feed(homeworks, incoming)
        ret_list.append(gen_data)

        _LOGGER.info("accessing homeworks")
        grades = get_grades(self._token, self._student_id)
        gen_data = generate_grades_feed(grades)
        ret_list.append(gen_data)

        return ret_list


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
        lesson = item.get("lesson", {})
        lesson_name = lesson.get("name")
        lesson_date = lesson.get("date")
        lesson_subject = lesson.get("subject")
        attend_status = item.get("status")
        status_label = ATTEND_STATUS_DICT.get(attend_status, attend_status)
        # pprint.pprint(item)
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
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

    content = dumps_feed_gen(feed_gen)
    return {"attendance.xml": content}


HW_STATUS_DICT = {0: "Niesprawdzona", 1: "Odrobione", 2: "Częsciowo odrobione", 3: "<b>Nieodrobione</b>"}


def generate_homeworks_feed(homework, incoming):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Prace domowe")
    feed_gen.description("prace domowe")

    hw_list = homework.get("results", [])
    for item in hw_list:
        lesson = item.get("lesson", {})
        homework_subject = lesson.get("homeworkSubject")
        if not homework_subject:
            # no homework to do - skip
            continue
        lesson_date = lesson.get("date")
        lesson_subject = lesson.get("subject")
        homework_checked = lesson.get("homeworkChecked")
        homework_status = item.get("status")

        # pprint.pprint(item)
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
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

    hw_list = incoming.get("results", [])
    for item in hw_list:
        homework_subject = item.get("homeworkSubject")
        if not homework_subject:
            # no homework to do - skip
            continue
        homework_date = item.get("date")

        # pprint.pprint(item)
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
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

    content = dumps_feed_gen(feed_gen)
    return {"homework.xml": content}


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
        grade_desc = item.get("gradeDescription", {})
        description = grade_desc.get("description")
        grade_type = grade_desc.get("gradeCategory", {}).get("namePl")
        month = grade_desc.get("month")
        year = grade_desc.get("year")
        grade_month = grade_desc.get("lesson", {}).get("date")
        grade_datetime = datetime.datetime(year=year, month=month, day=1)
        grade_datetime = add_timezone(grade_datetime)
        grade = item.get("grades", {}).get("_gradeFormat")
        grade_points = item.get("points")
        grade_points_max = item.get("pointsMax")
        grade_perc = None
        if grade_points is not None and grade_points_max is not None:
            grade_perc = grade_points / grade_points_max
        grade_meaning = get_grade_meaning(grade, grade_perc)

        # pprint.pprint(item)
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
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

    content = dumps_feed_gen(feed_gen)
    return {"grade.xml": content}


# ============================================================


def get_generator() -> RSSGenerator:
    return EarlyStageGenerator()
