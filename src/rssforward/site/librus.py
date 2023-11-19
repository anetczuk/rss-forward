#
# Copyright (c) 2023, Arkadiusz Netczuk <dev.arnet@gmail.com>
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#

# pylint: disable=E0401

import pprint

# from datetime import datetime

from librus_apix.get_token import get_token
from librus_apix.grades import get_grades

# from librus_apix.announcements import get_announcements
# from librus_apix.attendance import get_attendance
# from librus_apix.homework import get_homework, homework_detail
# from librus_apix.messages import get_recieved, message_content
# from librus_apix.schedule import get_schedule, schedule_detail
# from librus_apix.timetable import get_timetable

from rssforward.keepass.keepassauth import get_auth_data


def write_data(file_path, content):
    with open(file_path, "w", encoding="utf8") as fp:
        fp.write(content)


def librus_api():
    # #TODO: extract URL to config file or config settings
    auth_data = get_auth_data("https://portal.librus.pl/rodzina/synergia/loguj")

    username = auth_data.get("login")
    password = auth_data.get("password")

    token = get_token(username, password)

    print("========= grades =========")
    grades, average_grades = get_grades(token)
    pprint.pprint(grades)
    pprint.pprint(average_grades)

    # for semester in grades:
    #     pprint.pprint(grades[semester])
    #     for mark in grades[semester]["Mathematics"]:
    #         print(mark.grade)

    # print("========= announcements =========")
    # announcements = get_announcements(token)
    # for a in announcements:
    #     print(a.title)
    #
    # print("========= attendance =========")
    # first_semester, second_semester = get_attendance(token)
    # for attendance in first_semester:
    #     print(attendance.symbol, attendance.date)
    # for attendance in second_semester:
    #     print(attendance.symbol, attendance.date)
    #
    # print("========= homework =========")
    # # date from-to up to 1 month
    # date_from = '2023-10-02'
    # date_to = '2023-10-30'
    # homework = get_homework(token, date_from, date_to)
    # for h in homework:
    #     print(h.lesson, h.completion_date)
    #     href = h.href
    #     details = homework_detail(token, href)
    #     print(details)
    #
    # print("========= messages =========")
    # messages = get_recieved(token, page=1)
    # for message in messages:
    #     print(message.title)
    #     #href = message.href
    #     #print(message_content(token, href))
    #
    # print("========= schedule =========")
    # month = '10'
    # year = '2023'
    # schedule = get_schedule(token, month, year)
    # for day in schedule:
    #     for event in schedule[day]:
    #         print(event.title)
    #         #prefix, href = event.href.split('/')
    #         #details = schedule_detail(token, prefix, href)
    #         #print(details)
    #
    # print("========= timetable =========")
    # monday_date = '2023-11-6'
    # monday_datetime = datetime.strptime(monday_date, '%Y-%m-%d')
    # timetable = get_timetable(token, monday_datetime)
    # for weekday in timetable:
    #     for period in timetable[weekday]:
    #         print(period.subject, period.teacher_and_classroom)


def run():
    librus_api()
