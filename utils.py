#!/usr/bin/env python3
# -*- coding: utf-8  -*-
'''
This script provides functions to support localization and
formatting features for the Central Kurdish Wikipedia (ckbwiki).
It includes functions to convert numerals to Eastern Arabic numerals
and format dates according to the desired ckbwiki format.
The script is open for further contributions to enhance localization
and other related functionalities.
'''
#
# Authors: (C) User:Aram, 2023
# Last Updated: 1 December 2023
# License: Distributed under the terms of the MIT license.
# Version: 1.0
#

# A function to convert numerals to Eastern Arabic numerals
def convert_numerals(text):
    eastern_arabic_numerals = {
        '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
    }
    return ''.join(eastern_arabic_numerals[char] if char in eastern_arabic_numerals else char for char in text)

# A function to format a date with the Central Kurdish Wikipedia (ckbwiki) desired format and optional link
def format_date(date, link=None):
    months = {
        'January': 'کانوونی دووەم', 'February': 'شوبات', 'March': 'ئازار', 'April': 'نیسان', 'May': 'ئایار', 'June': 'حوزەیران',
        'July': 'تەممووز', 'August': 'ئاب', 'September': 'ئەیلوول', 'October': 'تشرینی یەکەم', 'November': 'تشرینی دووەم', 'December': 'کانوونی یەکەم'
    }

    date_parts = date.split()
    formatted_date = f'{convert_numerals(date_parts[2])}ی {months[date_parts[1]]}ی {convert_numerals(date_parts[0])}'
    if link:
        return f'[[{link}|{formatted_date}]]'
    else:
        return formatted_date