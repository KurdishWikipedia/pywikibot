#!/usr/bin/env python3
# -*- coding: utf-8  -*-
"""
Inactive Users Script

DISCLAIMER AND WARNINGS: THIS SCRIPT COMES WITH NO WARRANTY. USE AT YOUR OWN RISK.
THE AUTHORS AND CONTRIBUTORS OF THIS SCRIPT SHALL NOT BE HELD RESPONSIBLE FOR ANY DAMAGES,
LOSSES, OR LEGAL ISSUES ARISING FROM THE USE OF THIS SCRIPT.

Description:
This script retrieves inactive user statistics from a MySQL database and updates a target wiki page with the information.

Dependencies:
- pymysql: A Python library for MySQL database interactions.
Documentation: [https://pymysql.readthedocs.io/en/latest/]

- pywikibot: A Python library to interact with MediaWiki wikis.
Documentation: [https://www.mediawiki.org/wiki/Manual:Pywikibot]

Usage:
1. Configure the parameters below according to your project's needs.
2. Tranlsate some strings into your language (such as: table headers, etc.)
3. Run the script to retrieve and generate statistics for inactive users.
4. The generated table is updated on a specified wiki page.

Note: This script is customized for Kurdish Wikipedia (ckb.wikipedia.org),
and may require adjustments for other wikis.
"""
#
# Authors: (C) User:Aram, 2023
# Last Updated: 1 December 2023
# License: Distributed under the terms of the MIT license.
# Version: 1.0
#
import pymysql
import pywikibot
import logging
import re
from utils import convert_numerals, format_date

# Configuration Parameters
site_lang = 'ckb'  # Language code for the target site
site_family = 'wikipedia'  # Family name for the target site
bot_username = 'AramBot'  # Username of the bot making the update
page_title = 'ویکیپیدیا:ڕاپۆرتی بنکەدراوە/پێڕستی بەکارھێنەرە ناچالاکەکان'  # Title of the target statistics page
edit_summary = 'بۆت: نوێکردنەوە'  # Edit summary for page updates

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InactiveUsersLogger")

def establish_database_connection():
    connection = pymysql.connect(
        host="ckbwiki.analytics.db.svc.wikimedia.cloud",  # Hostname of the database server
        database="ckbwiki_p",  # Name of the target database
        port=3306,  # Port number for the database server
        # user="",  # Add your actual database username credential (if not using Toolforge)
        # password="",  # Add your actual database password credential (if not using Toolforge)
        read_default_file="~/replica.my.cnf",  # path to the "my.cnf" file
        charset='utf8'
    )
    return connection

def update_page(page, updated_full_page_content):
    try:
        # Exclude anything inside <onlyinclude> tags from both contents
        existing_content = re.sub(r"<onlyinclude>.*?</onlyinclude>", '', page.text).strip()
        new_content = re.sub(r"<onlyinclude>.*?</onlyinclude>", '', updated_full_page_content).strip()

        if new_content != existing_content:
            page.text = updated_full_page_content
            page.save(summary=edit_summary, minor=True, botflag=True)
            logger.info("Page updated successfully!")
        else:
            logger.info("No changes needed. The page is already up to date.")
    except pywikibot.exceptions.EditConflictError as e:
        logger.warning("Skipping %s because of edit conflict: %s", page.title(), e)
    except pywikibot.exceptions.SpamblacklistError as error:
        logger.warning("Cannot change %s due to spam blacklist entry %s", page.title(), error.url)
    except Exception as e:
        logger.error("An error occurred while updating the page: %s", e)

def main():
    try:
        # Establish a connection to the database
        connection = establish_database_connection()

        cursor = connection.cursor()
        cursor.execute("USE ckbwiki_p;")

        query = """
        SELECT
          ROW_NUMBER() OVER (ORDER BY last_edit.last_edit_date DESC) AS row_number,
          user_name,
          DATE_FORMAT(user_registration, '%Y %M %e') AS user_registration,
          user_editcount,
          DATE_FORMAT(last_edit.last_edit_date, '%Y %M %e') AS last_edit_date,
          IFNULL(GROUP_CONCAT(ug_group), '') AS groups
        FROM
          user
        LEFT JOIN (
          SELECT
            actor_user,
            MAX(rev_timestamp) AS last_edit_date
          FROM
            revision
          JOIN
            actor ON rev_actor = actor_id
          GROUP BY
            actor_user
        ) AS last_edit ON user_id = last_edit.actor_user
        LEFT JOIN user_groups ON user_id = ug_user
        WHERE
          user_editcount > 100 -- Adjust the edit count threshold as needed
          AND (last_edit.last_edit_date IS NULL OR last_edit.last_edit_date <= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 6 MONTH), "%Y%m%d%H%i%s"))
          AND user_id NOT IN (
            SELECT
              ug_user
            FROM
              user_groups
            WHERE
              ug_group LIKE '%bot%'
          ) -- Exclude bot user groups
          AND NOT user_name RLIKE '[Bb][Oo][Tt]$' -- Exclude users with "bot" at the end in a case-insensitive manner
          AND user_name NOT IN ('KLBot2', 'BOTijo') -- Exclude specific bots; they are bots with no "bot" flag
        GROUP BY user_id
        ORDER BY
          last_edit.last_edit_date DESC;
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

        logger.info(f"Retrieving inactive user statistics from {site.hostname()} database...")

        # Set up page_top and page_bottom
        page_top = '{{/سەرپەڕە}}\n'
        page_top += '{{چینی ناوەند}}\n'
        page_top += "'''دوایین نوێکردنەوە لەلایەن {{subst:بب|" + bot_username + "}}'''؛ لە <onlyinclude>~~~~~</onlyinclude>\n"
        page_top += '{{کۆتایی}}\n'

        page_bottom = '\n[[پۆل:ڕاپۆرتی بنکەدراوەی ویکیپیدیا]]'

        # Set up the actual table
        table = ''
        if decoded_results:
            logger.info("Inactive user statistics retrieved successfully!")

            table += "{| class=\"wikitable sortable\" style=\"margin: auto;\"\n"
            table += "|+ بەکارھێنەرە ناچالاکەکان\n"
            table += "|-\n"
            table += "! # !! بەکارھێنەر !! ژمارەی دەستکارییەکان !! ڕێکەوتی خۆتۆمارکردن !! دوایین دەستکاری !! مافەکان\n"

            for row in decoded_results:
                row_number, username, reg_date, num_edits, last_edit_date, groups = row
                row_number = convert_numerals(str(row_number))
                username_link = f"[[بەکارھێنەر:{username}|{username}]]"
                num_edits = convert_numerals(str(num_edits))
                reg_date = format_date(reg_date)
                last_edit_date = format_date(last_edit_date, link=f'تایبەت:بەشدارییەکان/{username}')

                table += "|-\n"
                table += f"| {row_number} || {username_link} || {num_edits} || {reg_date} || {last_edit_date} || {groups}\n"

            table += "|}\n"

            # Combine the page content
            full_page_content = f"{page_top}{table}{page_bottom}"

            # Use the update_page function to update the page
            update_page(target_page, full_page_content)
            logger.info("Script terminated successfully.\n")

        else:
            logger.info("No results found from the query.")
    except Exception as e:
        logger.error("An error occurred: %s", str(e))

if __name__ == "__main__":
    main()
