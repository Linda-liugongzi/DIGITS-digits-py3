# Copyright (c) 2014-2017, NVIDIA CORPORATION.  All rights reserved.
# -*- coding: utf-8 -*-


import time
from flask_babel import lazy_gettext as _


def print_time(t, ref_time=None):
    lt = time.localtime(t)

    # ref_time is for testing
    if ref_time is None:
        now = time.localtime()
    else:
        now = time.localtime(ref_time)

    if lt.tm_year != now.tm_year:
        return time.strftime('%b %d %Y, %I:%M:%S %p', lt)
    elif lt.tm_mon != now.tm_mon:
        return time.strftime('%b %d, %I:%M:%S %p', lt)
    elif lt.tm_mday != now.tm_mday:
        return time.strftime('%a %b %d, %I:%M:%S %p', lt)
    else:
        return time.strftime('%I:%M:%S %p', lt)


def print_time_local(t, ref_time=None):
    lt = time.localtime(t)

    # ref_time is for testing
    if ref_time is None:
        now = time.localtime()
    else:
        now = time.localtime(ref_time)

    if lt.tm_year != now.tm_year:
        return time.strftime('%Y年%m月%d日 %H:%M:%S', lt)
    elif lt.tm_mon != now.tm_mon:
        return time.strftime('%m月%d日 %H:%M:%S', lt)
    elif lt.tm_mday != now.tm_mday:
        return time.strftime('%m月%d日 %H:%M:%S', lt)
    else:
        return time.strftime('%H:%M:%S', lt)


def print_time_diff_local(diff):
    if diff is None:
        return '?'

    if diff < 0:
        return 'Negative Time'

    total_seconds = int(diff)
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    def plural(number, name):
        return '%d %s%s' % (number, name, '' if number == 1 else '')

    def pair(number1, name1, number2, name2):
        if number2 > 0:
            return '%s %s' % (plural(number1, name1), plural(number2, name2))
        else:
            return '%s' % plural(number1, name1)

    if days >= 1:
        return pair(days, '天', hours, '小时')
    elif hours >= 1:
        return pair(hours, '小时', minutes, '分')
    elif minutes >= 1:
        return pair(minutes, '分', seconds, '秒')
    return plural(seconds, '秒')


def print_time_diff(diff):
    if diff is None:
        return '?'

    if diff < 0:
        return 'Negative Time'

    total_seconds = int(diff)
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    def plural(number, name):
        return '%d %s%s' % (number, name, '' if number == 1 else 's')

    def pair(number1, name1, number2, name2):
        if number2 > 0:
            return '%s, %s' % (plural(number1, name1), plural(number2, name2))
        else:
            return '%s' % plural(number1, name1)

    if days >= 1:
        return pair(days, _('day'), hours, _('hour'))
    elif hours >= 1:
        return pair(hours, _('hour'), minutes, _('minute'))
    elif minutes >= 1:
        return pair(minutes, _('minute'), seconds, _('second'))
    return plural(seconds, _('second'))



def print_time_diff_nosuffixes(diff):
    if diff is None:
        return '?'

    hours, rem = divmod(diff, 3600)
    minutes, seconds = divmod(rem, 60)
    return '{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(seconds))


def print_time_since(t):
    return print_time_diff(time.time() - t)
