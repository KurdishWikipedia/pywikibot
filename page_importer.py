#!/usr/bin/env python3
"""
This script automates the process of creating pages in a destination Wikimedia project 
(e.g., Central Kurdish Wiktionary) by copying the latest version of pages from a source 
Wikimedia project (e.g., English Wiktionary) using Pywikibot.

Key Features:
1. Copies content from the source project and creates new pages in the destination 
   project if they do not already exist.
2. Supports importing pages with the same title or a translated title.
3. Avoids overwriting existing pages in the destination project.
4. Handles Wikidata connections by linking or creating items for the imported pages 
   and their source counterparts.

The script does not use the Special:Import page but instead directly copies content 
via the Pywikibot library. Configuration variables define the source and destination 
projects, languages, and the list of page titles to process.
"""

import pywikibot

# Configuration variables
SOURCE_WIKI_LANG = "en"
SOURCE_WIKI_PROJECT = "wiktionary"
DEST_WIKI_LANG = "ckb"
DEST_WIKI_PROJECT = "wiktionary"

# List of page titles to import with optional corresponding destination titles
page_titles = [
    "Category:Xhosa language",  # Import with the same title
    ("Category:Zulu language", "پۆل:زمانی زوولوو"), # Import under different title
]

def import_page(source_site, destination_site, source_page_title, destination_page_title=None):
    # Function to import a page from the source wiki to the destination wiki
    destination_page_title = destination_page_title or source_page_title  # Use source title if destination title is not provided
    source_page = pywikibot.Page(source_site, source_page_title)
    text = source_page.text
    # Check if the page exists on the source wiki
    if not source_page.exists():
        print(f"Page '{source_page_title}' does not exist on the source wiki.")
        return
    # Import the page to the destination wiki if it doesn't already exist
    destination_page = pywikibot.Page(destination_site, destination_page_title)
    if destination_page.exists():
        print(f"Page '{destination_page_title}' already exists on the destination wiki. Skipping.")
        return destination_page
    try:
        destination_page.text = text
        destination_page.save(summary=f"بۆت: لە [[:en:{source_page_title}]] ھاوردە کرا")
        print(f"Page '{destination_page_title}' imported successfully.")
        return destination_page
    except Exception as e:
        print(f"Failed to import page '{destination_page_title}': {e}")
        return None

def handle_wikidata(page, source_page_title, destination_page_title=None):
    # Function to handle Wikidata connection for a given page
    destination_page_title = destination_page_title or source_page_title  # Use source title if destination title is not provided
    source_wiki_page = pywikibot.Page(pywikibot.Site(SOURCE_WIKI_LANG, SOURCE_WIKI_PROJECT), source_page_title)
    dest_wiki_page = pywikibot.Page(pywikibot.Site(DEST_WIKI_LANG, DEST_WIKI_PROJECT), destination_page_title)

    # Check if the source wiki page has a Wikidata item
    try:
        source_wiki_item = source_wiki_page.data_item()
        if source_wiki_item:
            print(f"Found existing Wikidata item '{source_wiki_item.title()}' for '{source_page_title}' on the source wiki.")

            # Add Central Kurdish sitelink to the existing item
            if not source_wiki_item.sitelinks.get(dest_wiki_page.site.dbName()):
                source_wiki_item.setSitelink(dest_wiki_page, summary=f"Adding {DEST_WIKI_LANG} sitelink: {destination_page_title}")
                print(f"Page '{destination_page_title}' connected to existing Wikidata item '{source_wiki_item.title()}'.")
            else:
                print(f"Page '{destination_page_title}' already connected to existing Wikidata item '{source_wiki_item.title()}'.")
            return source_wiki_item
    except pywikibot.exceptions.NoPageError:
        pass

    # Check if the destination wiki page has a Wikidata item
    try:
        dest_wiki_item = dest_wiki_page.data_item()
        if dest_wiki_item:
            print(f"Found existing Wikidata item '{dest_wiki_item.title()}' for '{destination_page_title}' on the destination wiki.")

            # Add English sitelink to the existing item
            if not dest_wiki_item.sitelinks.get(source_wiki_page.site.dbName()):
                dest_wiki_item.setSitelink(source_wiki_page, summary=f"Adding {SOURCE_WIKI_LANG} sitelink: {source_page_title}")
                print(f"Page '{source_page_title}' connected to existing Wikidata item '{dest_wiki_item.title()}'.")
            else:
                print(f"Page '{source_page_title}' already connected to existing Wikidata item '{dest_wiki_item.title()}'.")
            return dest_wiki_item
    except pywikibot.exceptions.NoPageError:
        pass

    # Check if the page is a redirect
    if dest_wiki_page.isRedirectPage():
        # Redirect page already exists and should not create a new Wikidata item
        print(f"Page '{destination_page_title}' is a redirect. No new Wikidata item created.")
        return None

    # If no existing Wikidata item found and not a redirect page, create a new one and add both sitelinks
    print("Creating a new Wikidata item...")
    try:
        site = pywikibot.Site("wikidata", "wikidata")
        repo = site.data_repository()
        new_item = pywikibot.ItemPage(repo)
        
        # Connect the destination wiki site links
        new_item.setSitelink(dest_wiki_page, summary=f"Adding {DEST_WIKI_LANG} sitelink: {destination_page_title}")
        new_item.setSitelink(source_wiki_page, summary=f"Adding {SOURCE_WIKI_LANG} sitelink: {source_page_title}")

        print(f"Page '{destination_page_title}' connected to new Wikidata item '{new_item.title()}'.")
        return new_item
    except Exception as e:
        print(f"Error creating or editing Wikidata item: {e}")
        return None

def main():
    source_site = pywikibot.Site(SOURCE_WIKI_LANG, SOURCE_WIKI_PROJECT)
    destination_site = pywikibot.Site(DEST_WIKI_LANG, DEST_WIKI_PROJECT)
    
    for item in page_titles:
        if isinstance(item, tuple):
            source_title, dest_title = item
        else:
            source_title = dest_title = item
        print("\n")
        print(f"Processing page '{source_title}' with destination title '{dest_title}':")
        page = import_page(source_site, destination_site, source_title, dest_title)
        if page:
            handle_wikidata(page, source_title, dest_title)

if __name__ == "__main__":
    main()
