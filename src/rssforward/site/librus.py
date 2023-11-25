#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import os
import logging
import datetime

# import pprint

from feedgen.feed import FeedGenerator

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

from rssforward import DATA_DIR
from rssforward.utils import read_recent_date, add_timezone, convert_to_html, string_to_date, string_to_datetime
from rssforward.access.keepassxcauth import get_auth_data
from rssforward.rssgenerator import RSSGenerator


_LOGGER = logging.getLogger(__name__)


#
class LibusGenerator(RSSGenerator):
    def __init__(self):
        super().__init__()
        self._username = None
        self._password = None
        self._token = None

    def authenticate(self):
        # #TODO: extract URL to config file or config settings
        auth_data = get_auth_data("https://portal.librus.pl/rodzina/synergia/loguj")

        self._username = auth_data.get("login")
        self._password = auth_data.get("password")
        self._getToken()

    def generate(self):
        _LOGGER.info("========== running librus scraper ==========")

        try:
            generate_content(self._token)
            return
        except TokenError as exc:
            _LOGGER.warning("token error - try one more time with new token (%s)", exc)

        self._getToken()
        generate_content(self._token)

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


def generate_content(token):
    if token is None:
        _LOGGER.warning("unable to generate content, because generator is not authenticated")

    recent_datetime = read_recent_date()
    _LOGGER.info("getting librus data, recent date: %s", recent_datetime)

    _LOGGER.info("accessing grades")
    grades, average_grades, grades_desc = get_grades(token)
    generate_grades_feed(grades, average_grades, grades_desc)

    _LOGGER.info("accessing attendance")
    first_semester, second_semester = get_attendance(token)
    attendence = first_semester + second_semester
    generate_attendance_feed(attendence)

    _LOGGER.info("accessing messages")
    messages = get_messages_by_date(token, recent_datetime)
    _LOGGER.info("got %s messages since reference date %s", len(messages), recent_datetime)
    generate_messages_feed(messages, token)

    _LOGGER.info("accessing announcements")
    announcements = get_announcements_by_date(token, recent_datetime)
    _LOGGER.info("got %s announcements since reference date %s", len(announcements), recent_datetime)
    generate_announcements_feed(announcements)

    # ========= schedule =========
    curr_dt = datetime.datetime.today()
    year = curr_dt.year
    month = curr_dt.month
    _LOGGER.info("accessing schedule in %s-%s", year, month)
    schedule = get_schedule(token, month, year)
    generate_schedule_feed(schedule, year, month)

    # ========= homework =========
    # date from-to up to 1 month
    # date_from = '2023-09-01'
    # date_to = '2023-09-30'
    start_dt = datetime.datetime.today()
    start_dt = start_dt.replace(day=1)
    start_dt = str(start_dt.date())
    end_dt = datetime.datetime.today()
    end_dt = end_dt.replace(day=28) + datetime.timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    end_dt = end_dt - datetime.timedelta(days=end_dt.day)
    end_dt = str(end_dt.date())
    _LOGGER.info("accessing homework: %s %s", start_dt, end_dt)
    homework = get_homework(token, start_dt, end_dt)
    generate_homework_feed(homework, token)

    # print("========= timetable =========")
    # monday_date = '2023-11-6'
    # monday_datetime = datetime.strptime(monday_date, '%Y-%m-%d')
    # timetable = get_timetable(token, monday_datetime)
    # for weekday in timetable:
    #     for period in timetable[weekday]:
    #         print(period.subject, period.teacher_and_classroom)

    # organizacja -> dyzury


def generate_grades_feed(grades, _, grades_desc):
    feed_gen = init_feed_gen()
    feed_gen.title("Oceny")
    feed_gen.description("oceny")

    for subjects in grades.values():
        for subject_grades in subjects.values():
            for item in subject_grades:
                feed_item = feed_gen.add_entry()
                # do not set id() - thunderbird will skip message if something changes
                # feed_item.id(item.href)
                feed_item.title(f"Nowa ocena {item.grade} z przedmiotu {item.title}")
                feed_item.author({"name": item.teacher, "email": item.teacher})
                # fill description
                item_desc = f"""\
Semestr: {item.semester}
{item.desc}
"""
                item_desc = convert_to_html(item_desc)
                feed_item.content(item_desc)
                # fill publish date
                item_date = string_to_date(item.date)
                feed_item.pubDate(item_date)

    for subjects in grades_desc.values():
        for subject_grades in subjects.values():
            for item in subject_grades:
                feed_item = feed_gen.add_entry()
                # do not set id() - thunderbird will skip message if something changes
                # feed_item.id(item.href)
                feed_item.title(f"Nowa ocena {item.grade} z przedmiotu {item.title}")
                feed_item.author({"name": item.teacher, "email": item.teacher})
                # fill description
                item_desc = f"""\
Semestr: {item.semester}
{item.desc}
"""
                item_desc = convert_to_html(item_desc)
                feed_item.content(item_desc)
                # fill publish date
                item_date = string_to_date(item.date)
                feed_item.pubDate(item_date)

    execute_generator(feed_gen, "grade.xml")


def generate_attendance_feed(attendence):
    feed_gen = init_feed_gen()
    feed_gen.title("Frekwencja")
    feed_gen.description("frekwencja")

    for item in attendence:
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
        feed_item.title(f"{item.type} {item.subject}")
        feed_item.author({"name": item.teacher, "email": item.teacher})
        # fill description
        item_desc = f"""\
Przedmiot: {item.subject}
Typ: {item.type}
Nr lekcji: {item.period}
Nauczyciel: {item.teacher}
Czy wycieczka: {item.excursion}
"""
        item_desc = convert_to_html(item_desc)
        feed_item.content(item_desc)
        # fill publish date
        item_date = string_to_date(item.date)
        feed_item.pubDate(item_date)

    execute_generator(feed_gen, "attendence.xml")


def generate_messages_feed(messages, token):
    feed_gen = init_feed_gen()
    feed_gen.title("Wiadomości")
    feed_gen.description("wiadomości")

    for item in messages:
        # pprint.pprint(item)
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
        feed_item.title(item.title)
        feed_item.author({"name": item.author, "email": item.author})
        # fill description
        href = item.href
        item_desc = message_content(token, href)
        item_desc = convert_to_html(item_desc)
        feed_item.content(item_desc)
        # fill publish date
        item_date = string_to_datetime(item.date)
        feed_item.pubDate(item_date)

    execute_generator(feed_gen, "message.xml")


def generate_announcements_feed(announcements):
    feed_gen = init_feed_gen()
    feed_gen.title("Ogłoszenia")
    feed_gen.description("ogłoszenia")

    for item in reversed(announcements):
        feed_item = feed_gen.add_entry()
        feed_item.title(item.title)
        feed_item.author({"name": item.author, "email": item.author})
        # fill description
        item_desc = item.description
        item_desc = convert_to_html(item_desc)
        feed_item.content(item_desc)
        # fill publish date
        item_date = string_to_date(item.date)
        feed_item.pubDate(item_date)

    execute_generator(feed_gen, "announcement.xml")


def generate_schedule_feed(schedule, year, month):
    feed_gen = init_feed_gen()
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
            item_date = add_timezone(item_date)
            feed_item = feed_gen.add_entry()
            feed_item.title(item.title)
            feed_item.author({"name": "Librus", "email": "Librus"})
            # fill description
            description = "\n".join(item.data)
            item_desc = f"""\
Data: {item_date}
Przedmiot: {item.subject}
Nr lekcji: {item.number}
Opis:
{description}
"""
            item_desc = convert_to_html(item_desc)
            feed_item.content(item_desc)
            # fill publish date
            feed_item.pubDate(item_date)

    execute_generator(feed_gen, "schedule.xml")


def generate_homework_feed(homework, token):
    feed_gen = init_feed_gen()
    feed_gen.title("Prace domowe")
    feed_gen.description("prace domowe")

    for item in homework:
        # pprint.pprint(item)
        feed_item = feed_gen.add_entry()
        # do not set id() - thunderbird will skip message if something changes
        # feed_item.id(item.href)
        feed_item.title(f"{item.lesson}: {item.subject}")
        feed_item.author({"name": item.teacher, "email": item.teacher})
        # fill description
        href = item.href
        item_details = homework_detail(token, href)
        item_desc = ""
        for key, val in item_details.items():
            item_desc += f"{key}: {val}\n"
        item_desc = convert_to_html(item_desc)
        feed_item.content(item_desc)
        # fill publish date
        task_date = item_details["Data udostępnienia"]
        item_date = string_to_date(task_date)
        feed_item.pubDate(item_date)

    execute_generator(feed_gen, "homework.xml")


# ============================================================


def init_feed_gen() -> FeedGenerator:
    feed_gen = FeedGenerator()
    feed_gen.link(href="https://synergia.librus.pl/")
    feed_gen.language("pl")
    return feed_gen


def execute_generator(feed_gen: FeedGenerator, out_file):
    items_num = len(feed_gen._FeedGenerator__feed_entries)  # pylint: disable=W0212
    out_dir = os.path.join(DATA_DIR, "librus")
    os.makedirs(out_dir, exist_ok=True)
    feed_path = os.path.join(out_dir, out_file)
    _LOGGER.info("generating %s feed items to file: %s", items_num, feed_path)
    feed_gen.rss_file(feed_path, pretty=True)


# ============================================================


def get_generator() -> RSSGenerator:
    return LibusGenerator()


def generate_feed():
    generator = get_generator()
    generator.authenticate()
    generator.generate()
