#!/usr/bin/env python3
# -*- coding: utf-8  -*-

"""
Inactive Bot Statistics Script

This script retrieves statistics about inactive bots on a MediaWiki site
and generates a table containing their information, including username,
last edit time, edit count, and bot groups. The script then updates a
designated wiki page with the generated table.

Dependencies:
- pywikibot: A Python library to interact with MediaWiki wikis.

Usage:
1. Configure the 'site' variable in the 'main' function to point to the target wiki.
2. Run the script to retrieve and generate statistics for inactive bots.
3. The generated table is updated on a specified wiki page.

Note: This script is customized for Kurdish Wikipedia (ckb.wikipedia.org),
and may require adjustments for other wikis.

"""
#
# Authors: (C) User:Aram, 2023
# Last Updated: 20 August 2023
# License: Distributed under the terms of the MIT license.
# Version: 1.0
#

import pywikibot
from datetime import datetime, timedelta

def retrieve_bot_statistics(site, batch_size=50):
    print(f"Retrieving bot statistics from {site.hostname()}...\n")
    bot_statistics = []
    continue_token = None

    while True:
        query_params = {
            'list': 'allusers',
            'augroup': 'bot',
            'auwitheditsonly': True,
            'aulimit': batch_size,
            'action': 'query',  # Specify the 'action' parameter
            'aucontinue': continue_token
        }

        request = pywikibot.data.api.Request(site=site, parameters=query_params)
        result = request.submit()

        print("Result:", result)  # Print the result for debugging

        if 'query' in result and 'allusers' in result['query']:
            bot_list = result['query']['allusers']
            for bot in bot_list:
                username = bot['name']
                latest_edit = get_latest_edit_time(site, username)  # Call a function to get the latest edit time
                edit_count = get_bot_edit_count(site, username)  # Call a function to get the bot edit count
                bot_statistics.append((username, latest_edit, edit_count))

        if 'continue' in result:
            continue_token = result['continue']['aucontinue']
        else:
            break

    print("Bot statistics retrieved successfully!\n")
    return bot_statistics

def get_latest_edit_time(site, username):
    user = pywikibot.User(site, username)
    contributions = list(user.contributions(total=1))  # Get all contributions

    print("Contributions:", contributions)  # Print contributions for debugging

    if contributions:
        timestamp = contributions[0][2]
        formatted_time = timestamp.strftime('%d %B %Y')
        return formatted_time

    return 'N/A'

def get_bot_edit_count(site, username):
    user = pywikibot.User(site, username)
    edit_count = 0

    for _ in user.contributions(total=None):  # Remove the total limit
        edit_count += 1

    return edit_count

def is_inactive(last_edit_time, inactive_threshold_months=6):
    if last_edit_time == 'N/A':
        return True

    now = datetime.utcnow()
    last_edit = datetime.strptime(last_edit_time, '%d %B %Y')
    time_since_last_edit = now - last_edit
    return time_since_last_edit > timedelta(days=inactive_threshold_months * 30)

def retrieve_inactive_bots(statistics, inactive_threshold_months=6):
    return [(username, last_edit, edit_count) for username, last_edit, edit_count in statistics if is_inactive(last_edit, inactive_threshold_months)]

def generate_statistics_table(statistics):
    print("Generating statistics table...\n")
    months = {
        'January': 'کانوونی دووەم', 'February': 'شوبات', 'March': 'ئازار', 'April': 'نیسان', 'May': 'ئایار', 'June': 'حوزەیران',
        'July': 'تەممووز', 'August': 'ئاب', 'September': 'ئەیلوول', 'October': 'تشرینی یەکەم', 'November': 'تشرینی دووەم', 'December': 'کانوونی یەکەم'
    }
    
    eastern_arabic_numerals = {
        '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
    }
    
    # Sort the statistics list based on the entire date in ascending order
    sorted_statistics = sorted(statistics, key=lambda x: datetime.strptime(x[1], '%d %B %Y'), reverse=False)
    
    site = pywikibot.Site('ckb', 'wikipedia')
    
    bot_groups = retrieve_bot_groups(site, sorted_statistics)
    
    table = '{{ئەمانەش ببینە|ویکیپیدیا:بۆتە ناچالاکەکان}}\n'
    table += '{{چینی ناوەند}}\n'
    table += 'پێرستی [[وپ:بۆت|بۆت]]ە ناچالاکەکانی ویکیپیدیا{{ھن}}\n'
    table += 'بۆتی ناچالاک بە بۆتێک دەڵێن کە لە ٦ مانگی ڕابردوو ھیچ [[تایبەت:بەشدارییەکان|بەشدارییەکی]] نەبووە.{{ھن}}\n'
    table += 'لە ئێستادا ئەم ئامارە ھەفتانە نوێ دەکرێتەوە.{{ھن}}\n'
    table += "'''دوایین نوێکردنەوە لەلایەن {{subst:بب|AramBot}}'''؛ لە ''~~~~~''\n"
    table += '{{کۆتایی}}\n\n'
    
    table += '{| class="wikitable sortable" style="margin: auto;"\n'
    table += '! # !! بەکارھێنەر !! دوایین دەستکاری !! ژمارەی دەستکارییەکان !! مافەکان\n'

    for i, (username, last_edit, edit_count) in enumerate(sorted_statistics, start=1):
        day, month_name, year = last_edit.split(" ")
        month = months[month_name]
        
        day = ''.join(eastern_arabic_numerals[digit] for digit in day if digit != '0')
        year = ''.join(eastern_arabic_numerals[digit] for digit in year)
        num = ''.join(eastern_arabic_numerals[digit] for digit in str(i))
        
        formatted_date = f'{day}ی {month}ی {year}'
        edit_count = ''.join(eastern_arabic_numerals[digit] for digit in str(get_bot_edit_count(site, username)))
        bot_group = bot_groups.get(username, 'Unknown')
        
        table += '|-\n'
        table += f'| {num} || [[بەکارھێنەر:{username}|{username}]] || [[تایبەت:بەشدارییەکان/{username}|{formatted_date}]] || {edit_count} || {bot_group}\n'

    table += '|}'
    table += '\n\n[[پۆل:ڕاپۆرتی بنکەدراوەی ویکیپیدیا]]'

    print("Table generated successfully!\n")
    return table

def retrieve_bot_groups(site, statistics):
    bot_groups = {}

    for username, _, _ in statistics:
        user = pywikibot.User(site, username)
        groups = user.groups()

        if 'bot' in groups:
            groups.remove('*') # Remove the default group
            bot_groups[username] = ', '.join(groups)
            if 'bot' not in bot_groups[username]:
                bot_groups[username] = 'bot, ' + bot_groups[username]

    return bot_groups

def edit_statistics_page(page, table_content):
    try:
        if page.text != table_content:  # Check if the page content has changed
            page.text = table_content
            page.save('بۆت: نوێکردنەوە', minor=True) # Edit summary
            print("Wiki page updated successfully!\n")
        else:
            print("No changes needed. The wiki page is already up to date.\n")
    except Exception as e:
        print(f"An error occurred while updating the wiki page: {e}\n")

def main():
    site = pywikibot.Site('ckb', 'wikipedia')
    try:
        bot_statistics = retrieve_bot_statistics(site)
        inactive_bots = retrieve_inactive_bots(bot_statistics)

        if not inactive_bots:
            print("No inactive bots found.")
            return

        statistics_table = generate_statistics_table(inactive_bots)

        page_title = 'ویکیپیدیا:ڕاپۆرتی بنکەدراوە/پێڕستی بۆتە ناچالاکەکان'
        page = pywikibot.Page(site, page_title)

        edit_statistics_page(page, statistics_table)
    except Exception as e:
        print(f"An error occurred: {e}\n")
        return  # Exit the function if an error occurs

    print("Script completed successfully.")

if __name__ == '__main__':
    main()
