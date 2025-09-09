#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401 (import-error)

import logging
from typing import Dict
import datetime

from librus_apix.exceptions import MaintananceError, TokenError
from librus_apix.get_token import get_token
from librus_apix.grades import get_grades
from librus_apix.announcements import get_announcements
from librus_apix.attendance import get_attendance
from librus_apix.homework import get_homework, homework_detail
from librus_apix.messages import get_recieved, message_content, get_max_page_number
from librus_apix.schedule import get_schedule

# from librus_apix.schedule import schedule_detail
# from librus_apix.timetable import get_timetable

from rssforward.utils import read_recent_date, convert_to_html, string_to_date, string_to_datetime, calculate_dict_hash
from rssforward.rssgenerator import RSSGenerator
from rssforward.rss.utils import init_feed_gen, dumps_feed_gen


_LOGGER = logging.getLogger(__name__)


MAIN_URL = "https://synergia.librus.pl/"


#
class LibusGenerator(RSSGenerator):
    def __init__(self):
        super().__init__()
        self._username = None
        self._password = None
        self._token = None

    def authenticate(self, login, password):
        self._username = login
        self._password = password
        self._getToken()
        return True

    def generate(self) -> Dict[str, str]:
        _LOGGER.info("========== running librus scraper ==========")

        try:
            return generate_content(self._token)
        except TokenError as exc:
            _LOGGER.debug("token error - try one more time with new token (%s)", exc)

        self._getToken()
        return generate_content(self._token)

    def _getToken(self):
        self._token = None
        try:
            self._token = get_token(self._username, self._password)
        except MaintananceError as exc:
            _LOGGER.warning("librus system under maintenance: %s", exc)


# ============================================


def get_messages_by_date(token, start_datetime=None):
    ret_messages = []
    max_page_index = get_max_page_number(token)
    for pi in range(0, max_page_index + 1):
        messages = get_recieved(token, page=pi)
        _LOGGER.info("received %s messages from page %s", len(messages), pi)
        for item in messages:
            item_date = string_to_datetime(item.date)
            if start_datetime and item_date < start_datetime:
                return ret_messages
            ret_messages.append(item)
    return ret_messages


def get_announcements_by_date(token, start_datetime=None):
    ret_announcements = []
    announcements = get_announcements(token)
    _LOGGER.info("received %s announcements", len(announcements))
    for item in announcements:
        item_date = string_to_date(item.date)
        if start_datetime and item_date < start_datetime:
            return ret_announcements
        ret_announcements.append(item)
    return ret_announcements


def generate_content(token) -> Dict[str, str]:
    if token is None:
        _LOGGER.warning("unable to generate content, because generator is not authenticated")
        return None

    ret_dict: Dict[str, str] = {}

    recent_datetime = read_recent_date()
    _LOGGER.info("getting librus data, recent date: %s", recent_datetime)

    _LOGGER.info("accessing grades")
    grades, average_grades, grades_desc = get_grades(token)
    gen_data = generate_grades_feed(grades, average_grades, grades_desc)
    ret_dict.update(gen_data)

    _LOGGER.info("accessing attendance")
    first_semester, second_semester = get_attendance(token)
    attendence = first_semester + second_semester
    gen_data = generate_attendance_feed(attendence)
    ret_dict.update(gen_data)

    _LOGGER.info("accessing messages")
    messages = get_messages_by_date(token, recent_datetime)
    _LOGGER.info("got %s messages since reference date %s", len(messages), recent_datetime)
    gen_data = generate_messages_feed(messages, token)
    ret_dict.update(gen_data)

    _LOGGER.info("accessing announcements")
    announcements = get_announcements_by_date(token, recent_datetime)
    _LOGGER.info("got %s announcements since reference date %s", len(announcements), recent_datetime)
    gen_data = generate_announcements_feed(announcements)
    ret_dict.update(gen_data)

    # ========= schedule =========
    curr_dt = datetime.datetime.today()
    year = curr_dt.year
    month = curr_dt.month
    _LOGGER.info("accessing schedule in %s-%s", year, month)
    schedule = get_schedule(token, month, year)
    gen_data = generate_schedule_feed(schedule, year, month)
    ret_dict.update(gen_data)

    # ========= homework =========
    # date from-to up to 1 month
    # date_from = '2023-09-01'
    # date_to = '2023-09-30'
    start_dt = datetime.datetime.today()
    start_dt = start_dt.replace(day=1)
    end_dt = datetime.datetime.today()
    end_dt = end_dt.replace(day=28) + datetime.timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    end_dt = end_dt - datetime.timedelta(days=end_dt.day)
    start_dt_str = start_dt.date().strftime("%Y-%m-%d")
    # start_dt_str = str(start_dt.date())
    end_dt_str = end_dt.date().strftime("%Y-%m-%d")
    # end_dt = str(end_dt.date())
    _LOGGER.info("accessing homework: %s %s", start_dt_str, end_dt_str)
    homework = get_homework(token, start_dt_str, end_dt_str)  # dates in format %Y-%m-%d
    gen_data = generate_homework_feed(homework, token)
    ret_dict.update(gen_data)

    # print("========= timetable =========")
    # monday_date = '2023-11-6'
    # monday_datetime = datetime.strptime(monday_date, '%Y-%m-%d')
    # timetable = get_timetable(token, monday_datetime)
    # for weekday in timetable:
    #     for period in timetable[weekday]:
    #         print(period.subject, period.teacher_and_classroom)

    # organizacja -> dyzury

    return ret_dict


def generate_grades_feed(grades, _, grades_desc):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Oceny")
    feed_gen.description("oceny")

    # grades: List of semesters
    for sem_grades in grades:
        # sem_grades: Dict of subject and list of grades
        for subject_grades in sem_grades.values():
            for item in subject_grades:
                data_dict = {
                    "item_date": item.date,
                    "teacher": item.teacher,
                    "title": item.title,
                    "grade": item.grade,
                    "semester": item.semester,
                    "description": item.desc,
                }
                add_grade_numeric(feed_gen, data_dict)

    # grades: List of semesters
    for sem_grades in grades_desc:
        # sem_grades: Dict of subject and list of grades
        for subject_grades in sem_grades.values():
            for item in subject_grades:
                data_dict = {
                    "item_date": item.date,
                    "teacher": item.teacher,
                    "title": item.title,
                    "grade": item.grade,
                    "semester": item.semester,
                    "description": item.desc,
                }
                add_grade_descriptive(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"grade.xml": content}


def add_grade_numeric(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    teacher = data_dict["teacher"]
    title = data_dict["title"]
    grade = data_dict["grade"]
    semester = data_dict["semester"]
    description = data_dict["description"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"Nowa ocena {grade} z przedmiotu {title}")
    feed_item.author({"name": teacher, "email": teacher})
    # fill description
    item_desc = f"""\
Semestr: {semester}
{description}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(item_date)
    feed_item.pubDate(item_date)


def add_grade_descriptive(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    teacher = data_dict["teacher"]
    title = data_dict["title"]
    grade = data_dict["grade"]
    semester = data_dict["semester"]
    description = data_dict["description"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"Nowa ocena {grade} z przedmiotu {title}")
    feed_item.author({"name": teacher, "email": teacher})
    # fill description
    item_desc = f"""\
Semestr: {semester}
{description}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(item_date)
    feed_item.pubDate(item_date)


def generate_attendance_feed(attendence):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Frekwencja")
    feed_gen.description("frekwencja")

    for item in attendence:
        data_dict = {
            "item_date": item.date,
            "teacher": item.teacher,
            "subject": item.subject,
            "type": item.type,
            "period": item.period,
            "excursion": item.excursion,
        }
        add_attendance(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"attendence.xml": content}


def add_attendance(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    teacher = data_dict["teacher"]
    subject = data_dict["subject"]
    item_type = data_dict["type"]
    period = data_dict["period"]
    excursion = data_dict["excursion"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"{item_type} {subject}")
    feed_item.author({"name": teacher, "email": teacher})
    # fill description
    item_desc = f"""\
Przedmiot: {subject}
Typ: {item_type}
Nr lekcji: {period}
Nauczyciel: {teacher}
Czy wycieczka: {excursion}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(item_date)
    feed_item.pubDate(item_date)


def generate_messages_feed(messages, token):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Wiadomości")
    feed_gen.description("wiadomości")

    for item in messages:
        # pprint.pprint(item)
        item_desc = message_content(token, item.href)
        data_dict = {
            "item_date": item.date,
            "title": item.title,
            "author": item.author,
            "content": item_desc,
            "has_attachment": item.has_attachment,
        }
        add_message(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"message.xml": content}


def add_message(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    title = data_dict["title"]
    author = data_dict["author"]
    item_desc = data_dict["content"]
    if data_dict["has_attachment"]:
        item_desc += "\n\n=== wiadomość zawiera załącznik - do pobrania poprzez Librus ==="

    feed_item = feed_gen.add_entry()

    item_date = string_to_datetime(item_date)
    item_date_str = item_date.strftime("%Y-%m-%d")
    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date_str}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(title)
    feed_item.author({"name": author, "email": author})
    # fill description
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    feed_item.pubDate(item_date)


def generate_announcements_feed(announcements):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Ogłoszenia")
    feed_gen.description("ogłoszenia")

    for item in reversed(announcements):
        data_dict = {
            "item_date": item.date,
            "title": item.title,
            "author": item.author,
            "description": item.description,
        }
        add_announcement(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"announcement.xml": content}


def add_announcement(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    title = data_dict["title"]
    author = data_dict["author"]
    description = data_dict["description"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(title)
    feed_item.author({"name": author, "email": author})
    # fill description
    item_desc = description
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(item_date)
    feed_item.pubDate(item_date)


def generate_schedule_feed(schedule, year, month):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Terminarz")
    feed_gen.description("terminarz")

    for event_list in schedule.values():
        for item in event_list:
            # if item.href:
            #     # href is optional. Is filled in case of presence of details of event
            #     prefix, href = item.href.split('/')
            #     details = schedule_detail(token, prefix, href)
            #     pprint.pprint(details)

            item_date = datetime.datetime(year, month, int(item.day))
            item_date_str = item_date.strftime("%Y-%m-%d")

            data_dict = {
                "item_date": item_date_str,
                "title": item.title,
                "subject": item.subject,
                "number": item.number,
                "description": item.data,
            }
            add_schedule(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"schedule.xml": content}


def add_schedule(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    title = data_dict["title"]
    subject = data_dict["subject"]
    number = data_dict["number"]
    description = data_dict["description"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(title)
    feed_item.author({"name": "Librus", "email": "Librus"})
    # fill description
    description = "\n".join(description)
    item_desc = f"""\
Data: {item_date}
Przedmiot: {subject}
Nr lekcji: {number}
Opis:
{description}
"""
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    item_date = string_to_date(item_date)
    feed_item.pubDate(item_date)


def generate_homework_feed(homework, token):
    feed_gen = init_feed_gen(MAIN_URL)
    feed_gen.title("Prace domowe")
    feed_gen.description("prace domowe")

    for item in homework:
        # pprint.pprint(item)
        item_details = homework_detail(token, item.href)
        task_date = item_details["Data udostępnienia"]
        item_date = string_to_date(task_date)

        item_desc = ""
        for key, val in item_details.items():
            item_desc += f"{key}: {val}\n"

        data_dict = {
            "item_date": item_date,
            "title": item.title,
            "subject": item.subject,
            "number": item.number,
            "description": item_desc,
        }
        add_homework(feed_gen, data_dict)

    content = dumps_feed_gen(feed_gen)
    return {"homework.xml": content}


def add_homework(feed_gen, data_dict):
    item_date = data_dict["item_date"]
    teacher = data_dict["teacher"]
    subject = data_dict["subject"]
    lesson = data_dict["lesson"]
    item_desc = data_dict["description"]

    feed_item = feed_gen.add_entry()

    data_hash = calculate_dict_hash(data_dict)
    item_id = f"{item_date}_{data_hash}"  # add date to prevent hash collision (very unlikely, but still...)
    feed_item.id(item_id)

    feed_item.title(f"{lesson}: {subject}")
    feed_item.author({"name": teacher, "email": teacher})
    # fill description
    item_desc = convert_to_html(item_desc)
    feed_item.content(item_desc)
    # fill publish date
    feed_item.pubDate(item_date)


# ============================================================


def get_generator(_gen_params=None) -> RSSGenerator:
    return LibusGenerator()
