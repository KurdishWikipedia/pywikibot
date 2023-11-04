#!/usr/bin/env python3
# -*- coding: utf-8  -*-

"""
Inactive Bot Statistics Script

DISCLAIMER AND WARNINGS: THIS SCRIPT COMES WITH NO WARRANTY. USE AT YOUR OWN RISK.
THE AUTHORS AND CONTRIBUTORS OF THIS SCRIPT SHALL NOT BE HELD RESPONSIBLE FOR ANY DAMAGES,
LOSSES, OR LEGAL ISSUES ARISING FROM THE USE OF THIS SCRIPT.

Description:
This script retrieves statistics about inactive bots on a MediaWiki site
and generates a table containing their information, including username,
last edit time, edit count, bot groups and registration date.
The script then updates a designated wiki page with the generated table.

Dependencies:
- pymysql: A Python library for MySQL database interactions.
Documentation: [https://pymysql.readthedocs.io/en/latest/]

- pywikibot: A Python library to interact with MediaWiki wikis.
Documentation: [https://www.mediawiki.org/wiki/Manual:Pywikibot]

Usage:
1. Configure the parameters below according to your project's needs.
2. Tranlsate some strings into your language (such as: table headers, etc.)
3. Run the script to retrieve and generate statistics for inactive bots.
4. The generated table is updated on a specified wiki page.

Note: This script is customized for Kurdish Wikipedia (ckb.wikipedia.org),
and may require adjustments for other wikis.

"""
#
# Authors: (C) User:Aram, 2023
# Last Updated: 1 November 2023
# License: Distributed under the terms of the MIT license.
# Version: 1.2
#

import pymysql
import pywikibot
import logging
import re

# Configuration Parameters
site_lang = 'ckb'  # Language code for the target site
site_family = 'wikipedia'  # Family name for the target site
bot_username = 'AramBot'  # Username of the bot making the update
page_title = 'ویکیپیدیا:ڕاپۆرتی بنکەدراوە/پێڕستی بۆتە ناچالاکەکان'  # Title of the target statistics page
edit_summary = 'بۆت: نوێکردنەوە'  # Edit summary for page updates

# Database connection details
# Note: If you are using Toolforge, you may ignore the database username and password
db_hostname_format = "ckbwiki.analytics.db.svc.wikimedia.cloud"  # Hostname of the database server
db_port = 3306  # Port number for the database server
# db_username = ""  # Add your actual database username credential (if not using Toolforge)
# db_password = ""  # Add your actual database password credential (if not using Toolforge)
db_name_format = "ckbwiki_p"  # Name of the target database
db_connect_file = "~/replica.my.cnf" # path to the "my.cnf" file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InctiveBotsLogger")

# Create a connection to the database
try:
    connection = pymysql.connect(
        host=db_hostname_format,
        port=db_port,
        # user=db_username,
        # password=db_password,
        read_default_file=db_connect_file, # "my.cnf" file contains user and password and read these parameters from under the [client] section.
        charset='utf8'
    )

    # Define a function to convert numerals to Eastern Arabic numerals
    def convert_numerals(text):
        eastern_arabic_numerals = {
            '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
        }
        return ''.join(eastern_arabic_numerals[char] if char in eastern_arabic_numerals else char for char in text)

    # Define a function to format a date with the desired format and optional link
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

    cursor = connection.cursor()
    cursor.execute("USE ckbwiki_p;")

    query = """
    WITH InactiveBotsData AS (
        SELECT
            actor_name AS Username,
            MAX(rev_timestamp) AS LastEditTimestamp,
            COUNT(rev_id) AS NumberOfEdits,
            GROUP_CONCAT(DISTINCT actor_user_groups.ug_group) AS BotGroups,
            user_registration AS RegistrationTimestamp
        FROM revision
        JOIN actor ON actor_id = rev_actor
        JOIN user ON actor_user = user_id
        LEFT JOIN user_groups AS actor_user_groups ON user_id = actor_user_groups.ug_user
        WHERE actor_user_groups.ug_group LIKE '%bot%'
        GROUP BY Username
        HAVING LastEditTimestamp < DATE_FORMAT(NOW() - INTERVAL 30 DAY, '%Y%m%d%H%i%s') -- Change '30 DAY' to the desired inactivity threshold
    )
    
    SELECT
        ROW_NUMBER() OVER (ORDER BY LastEditTimestamp ASC) AS '#',
        Username,
        DATE_FORMAT(LastEditTimestamp, '%Y %M %e') AS LastEditDate,
        NumberOfEdits,
        BotGroups,
        DATE_FORMAT(RegistrationTimestamp, '%Y %M %e') AS RegistrationDate
    FROM InactiveBotsData
    ORDER BY LastEditTimestamp ASC;
    """

    cursor.execute(query)
    results = cursor.fetchall()
    decoded_results = []

    for row in results:
        decoded_row = [item.decode('utf-8') if isinstance(item, bytes) else str(item) for item in row]
        decoded_results.append(decoded_row)

    cursor.close()
    connection.close()

    site = pywikibot.Site(site_lang, site_family)
    target_page = pywikibot.Page(site, page_title)
    
    logger.info(f"Retrieving inactive bot statistics from {site.hostname()} database...")

    table = '{{ئەمانەش ببینە|ویکیپیدیا:بۆتە ناچالاکەکان|ویکیپیدیا:ڕاپۆرتی بنکەدراوە/پێڕستی بۆتە چالاکەکان}}\n'
    table += '{{چینی ناوەند}}\n'
    table += 'پێرستی [[وپ:بۆت|بۆت]]ە ناچالاکەکانی ویکیپیدیا{{ھن}}\n'
    table += 'بۆتی ناچالاک بە بۆتێک دەڵێن کە لە ٣٠ ڕۆژی ڕابردوو ھیچ [[تایبەت:بەشدارییەکان|بەشدارییەکی]] نەبووە.{{ھن}}\n'
    table += 'لە ئێستادا ئەم ئامارە ڕۆژانە نوێ دەکرێتەوە.{{ھن}}\n'
    table += "'''دوایین نوێکردنەوە لەلایەن {{subst:بب|" + bot_username + "}}'''؛ لە ''~~~~~''\n"
    table += '{{کۆتایی}}\n'

    if decoded_results:
        logger.info("Inctive bot statistics retrieved successfully!")

        table += "{| class=\"wikitable sortable\" style=\"margin: auto;\"\n"
        table += "|+ بۆتە ناچالاکەکان\n"
        table += "|-\n"
        table += "! # !! بەکارھێنەر !! دوایین دەستکاری !! ژمارەی دەستکارییەکان !! مافەکان !! ڕێکەوتی خۆتۆمارکردن\n"

        for row in decoded_results:
            rank, username, last_edit_date, num_edits, bot_groups, reg_date = row
            rank = convert_numerals(str(rank))
            num_edits = convert_numerals(str(num_edits))
            last_edit_date = format_date(last_edit_date, link=f'تایبەت:بەشدارییەکان/{username}')
            reg_date = format_date(reg_date)

            table += "|-\n"
            table += f"| {rank} || [[بەکارھێنەر:{username}|{username}]] || {last_edit_date} || {num_edits} || {bot_groups} || {reg_date}\n"

        table += "|}\n"
        table += '\n[[پۆل:ڕاپۆرتی بنکەدراوەی ویکیپیدیا]]'

        # Define the update_page function
        def update_page(page, table_content):
            try:
                # Remove the timestamp from the existing page content
                existing_content_without_timestamp = re.sub(r".+دوایین نوێکردنەوە لەلایەن.+", '', page.text).strip()

                # Remove the timestamp from the new table content
                new_content_without_timestamp = re.sub(r".+دوایین نوێکردنەوە لەلایەن.+", '', table_content).strip()

                if new_content_without_timestamp != existing_content_without_timestamp:
                    page.text = table_content
                    page.save(summary=edit_summary, minor=True, botflag=True)
                    logger.info("Page updated successfully!")
                else:
                    logger.info("No changes needed. The page is already up to date.")
            except Exception as e:
                logger.error("An error occurred while updating the page: %s", e)

        # Use the update_page function to update the page
        update_page(target_page, table)
        logger.info("Script terminated successfully.\n\n")
    else:
        logger.info("No results found from the query.")
except Exception as e:
    logger.error("An error occurred: %s", str(e))
    