#!/usr/bin/env python3
# -*- coding: utf-8  -*-
"""
The "important_categories" script, using SPARQL, searches for 
all categories created in most Wikimedia projects, but not yet 
created in your wiki, another Wikimedia project. It then lists 
all the categories and their interwiki numbers on a specific page.
"""
#
# Authors: (C) User:Aram, 2023
# Last Updated: December 13, 2023
# License: Distributed under the terms of the MIT license.
# Version: 1.0
#
import re
import pywikibot
from pywikibot.data import sparql
from utils import convert_numerals

# Configuration settings
site = pywikibot.Site("ckb", "wikipedia") # Define site language and site family
page_title = "ویکیپیدیا:ڕاپۆرتی بنکەدراوە/پۆلە گرنگە دروست نەکراوەکان" # Title of the target page
edit_summary = "بۆت: نوێکردنەوە" # Edit summary for page updates
bot_username = "AramBot" # Username of the bot making the update

def execute_sparql_query(endpoint_url, query):
    try:
        sparql_wd = sparql.SparqlQuery(endpoint=endpoint_url, entity_url=site.protocol() + site.hostname())
        result = sparql_wd.select(query)
        return result
    except Exception as e:
        print(f"Error executing SPARQL query: {e}")
        return None

def update_page(page_title, updated_full_page_content):
    page = pywikibot.Page(site, page_title)

    try:
        # Exclude anything inside <onlyinclude> tags from both contents
        existing_content = re.sub(r"<onlyinclude>.*?</onlyinclude>", '', page.text).strip()
        new_content = re.sub(r"<onlyinclude>.*?</onlyinclude>", '', updated_full_page_content).strip()

        # Check if the content has changed
        if existing_content != new_content:
            page.text = updated_full_page_content
            page.save(summary=edit_summary, minor=True, botflag=True)
        else:
            print(f"No changes needed for page \"{page_title}\"; updated already.")
    except Exception as e:
        print(f"Error updating page: {e}")

def main():

    # Show this message immediately
    print(f"Trying to update \"{page_title}\" of {site.hostname()}. Please wait...")
    
    # SPARQL query
    # User:TomT0m@wikidata is the original author of the first version of this query
    # See: https://w.wiki/8Uwv
    sparql_query = """
        SELECT ?item ?enLabel ?numOfSitelinks {
          ?item wdt:P31 wd:Q4167836 .
          ?item wikibase:sitelinks ?numOfSitelinks . hint:Prior hint:rangeSafe "true" .
          ?item rdfs:label ?enLabel.
          filter(lang(?enLabel) = "en")
          filter (?numOfSitelinks > 70) 
          MINUS {
            ?cat schema:isPartOf <https://ckb.wikipedia.org/> ;
                 schema:about ?item .
          }
        } ORDER BY DESC(?numOfSitelinks) LIMIT 1000
    """

    # Define the SPARQL endpoint
    sparql_endpoint = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"

    # Execute the SPARQL query
    query_result = execute_sparql_query(sparql_endpoint, sparql_query)

    # Set up page_top
    page_top = '{{/سەرپەڕە}}\n'
    page_top += "<onlyinclude>'''دوایین نوێکردنەوە لەلایەن {{subst:بب|" + bot_username + "}}'''؛ لە ~~~~~</onlyinclude>\n"

    # Set up the actual table
    table = ''

    if query_result:
        # Construct the new content for the page
        table = "{| class=\"wikitable sortable\"\n|-\n! ناوی پۆل بە ئینگلیزی !! ژمارەی{{ھن}}نێوانویکییەکان\n"
        
        for item in query_result:
            # Format the English label as a link to the English Wikipedia category page
            en_label_link = "[[:en:{}|{}]]".format(item['enLabel'], item['enLabel'])

            # Localizing numbers
            localized_numOfSitelinks = convert_numerals(str(item['numOfSitelinks']))
        
            table += "|-\n| {} || {}\n".format(en_label_link, localized_numOfSitelinks)
        
        table += "|}\n"

        # Set up page_bottom
        page_bottom = '\n[[پۆل:ڕاپۆرتی بنکەدراوەی ویکیپیدیا]]'

        # Combine the page content
        full_page_content = f"{page_top}{table}{page_bottom}"

        # Update and save the page
        update_page(page_title, full_page_content)
    else:
        print("No data retrieved from the SPARQL query.")

if __name__ == "__main__":
    main()
