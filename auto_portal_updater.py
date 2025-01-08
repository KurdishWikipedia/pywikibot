#!/usr/bin/env python3
"""
A bot to add portals from Arabic Wikipedia to Central Kurdish Wikipedia articles.

Parameters supported:
-always           The bot won't ask for confirmation when putting a page
-summary:         Set the action summary message for the edit.
"""

import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    AutomaticTWSummaryBot,
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
import requests
import re
from pywikibot.textlib import add_text

class PortalAdderBot(
    SingleSiteBot,
    ConfigParserBot,
    ExistingPageBot,
    AutomaticTWSummaryBot,
):
    use_redirects = False
    summary_key = 'portal-adding'

    update_options = {
        'summary': None,
        'always': False,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ckb_site = pywikibot.Site('ckb', 'wikipedia')
        self.ar_site = pywikibot.Site('ar', 'wikipedia')
        self.ckb_template_title = self.get_title_from_wikidata('Q11053759', 'ckb')
        self.ar_template_title = self.get_title_from_wikidata('Q11053759', 'ar')
        self.ckb_redirect_titles = self.get_all_template_redirects(self.ckb_site, self.ckb_template_title)
        self.ar_redirect_titles = self.get_all_template_redirects(self.ar_site, self.ar_template_title)
        # print(f"CKB template: {self.ckb_template_title}, redirects: {self.ckb_redirect_titles}")
        # print(f"AR template: {self.ar_template_title}, redirects: {self.ar_redirect_titles}")

    def get_title_from_wikidata(self, item_id, language):
        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={item_id}&props=sitelinks&languages={language}&format=json"
        response = requests.get(url)
        data = response.json()
        
        site_key = f"{language}wiki"
        if site_key in data['entities'][item_id]['sitelinks']:
            title = data['entities'][item_id]['sitelinks'][site_key]['title']
            title = title.split(':', 1)[-1]  # Remove the "Template:" prefix if present
            return title
        else:
            return None

    def get_all_template_redirects(self, site, tag_name):
        tag_page = pywikibot.Page(site, tag_name, ns=10)
        redirects = tag_page.redirects()
        redirect_titles = [redirect.title(with_ns=False) for redirect in redirects]
        return redirect_titles

    def get_existing_template(self, page_text, template_names):
        for template_name in template_names:
            pattern = re.compile(r'{{\s*' + re.escape(template_name) + r'(?:\|[^}]+)?\s*}}', re.IGNORECASE)
            match = pattern.search(page_text)
            if match:
                return match.group(0)
        return None

    def clean_template(self, template_text):
        cleaned_template = re.sub(r'\|\d+=', '|', template_text)
        cleaned_template = re.sub(r'\s*\|\s*', '|', cleaned_template)
        return cleaned_template

    def get_portals_from_template(self, template_text):
        portals = re.findall(r'\|([^}|]+)', template_text)
        return [p.strip() for p in portals if p.strip()]

    def convert_ar_to_ckb_portal(self, ar_portal):
        try:
            ar_page = pywikibot.Page(self.ar_site, f"بوابة:{ar_portal}")

            # Follow redirect if the portal is a redirect
            if ar_page.isRedirectPage():
                ar_page = ar_page.getRedirectTarget()

            if not ar_page.exists():
                return None

            try:
                item = pywikibot.ItemPage.fromPage(ar_page)
                if not item.exists():
                    return None

                try:
                    ckb_page = item.getSitelink(self.ckb_site)
                    return ckb_page.split(':', 1)[-1] if ':' in ckb_page else ckb_page
                except pywikibot.exceptions.NoSiteLinkError:
                    return None
            except pywikibot.exceptions.NoPageError:
                return None
        except Exception as e:
            print(f"Error converting AR portal '{ar_portal}' to CKB: {str(e)}")
            return None

        
    def ckb_portal_exists(self, portal_name):
        portal_page = pywikibot.Page(self.ckb_site, f"دەروازە:{portal_name}")
        return portal_page.exists()
    
    def make_sentence(self, array):
        if len(array) < 3:
            return ' و '.join(array)
        last = array.pop()
        return '، '.join(array) + ' و ' + last

    def make_portal_link(self, tag):
        text = '[['
        if '|' in tag:
            tag = tag[:tag.index('|')]
        text += tag if ':' in tag else f'دەروازە:{tag}|{tag}'
        return text + ']]'

    def get_tag_summary_prefix(self, num_tags):
        return "دەروازەی" if num_tags == 1 else "دەروازەکانی"
    
    def is_page_eligible_for_edit(self, page):
        if page.namespace() != 0:
            print("You are not allowed to use this script on other namespaces, but articles only and only.")
            return False
        
        if page.isDisambig():
            print("Page \"" + page.title() + "\" is a disambiguation page and is not eligible for editing.")
            return False
        
        return True

    def treat_page(self):
        ckb_page = self.current_page

        # Check if the page is eligible for edit
        if not self.is_page_eligible_for_edit(ckb_page):
            return  # Exit the method if page is not eligible

        try:
            ckb_item = pywikibot.ItemPage.fromPage(ckb_page)
            if not ckb_item.exists():
                print(f"Skipping; no Wikidata item found")
                return
        except pywikibot.exceptions.NoPageError:
            print(f"Skipping; not linked to Wikidata")
            return

        ar_site = pywikibot.Site('ar', 'wikipedia')
        try:
            ar_title = ckb_item.getSitelink(ar_site)
            ar_page = pywikibot.Page(ar_site, ar_title)
        except pywikibot.exceptions.NoSiteLinkError:
            print(f"Skipping; no corresponding Arabic article found in Wikidata")
            return

        if not ar_page.exists():
            print(f"Skipping {ckb_page.title()} - Corresponding Arabic article {ar_title} does not exist")
            return

        print(f"Found corresponding Arabic article: {ar_page.title()}")

        ar_text = ar_page.text
        ar_template = self.get_existing_template(ar_text, [self.ar_template_title] + self.ar_redirect_titles)

        if not ar_template:
            print(f"No portal template found in Arabic article.")
            return

        ar_portals = self.get_portals_from_template(ar_template)
        print(f"AR portals: {ar_portals}")

        # Convert AR portals to CKB and filter out non-existent portals
        ckb_portals = []
        skipped_portals = []
        for portal in ar_portals:
            ckb_portal = self.convert_ar_to_ckb_portal(portal)
            if ckb_portal and self.ckb_portal_exists(ckb_portal):
                ckb_portals.append(ckb_portal)
            else:
                skipped_portals.append(portal)

        if skipped_portals:
            print(f"Skipped portals (no corresponding CKB portal found): {skipped_portals}")

        print(f"Valid CKB portals: {ckb_portals}")

        ckb_text = ckb_page.text
        existing_ckb_template = self.get_existing_template(ckb_text, [self.ckb_template_title] + self.ckb_redirect_titles)

        new_portals = []
        if existing_ckb_template:
            existing_ckb_portals = self.get_portals_from_template(existing_ckb_template)
            new_portals = [p for p in ckb_portals if p not in existing_ckb_portals]
            if not new_portals:
                print(f"Skipped; no new portals to add.")
                return

            # Modify existing template
            all_portals = existing_ckb_portals + new_portals
            template_name = re.match(r'{{([^|]+)', existing_ckb_template).group(1).strip()
            new_template = '{{' + template_name + '|' + '|'.join(all_portals) + '}}'
            ckb_text = ckb_text.replace(existing_ckb_template, new_template)
        else:
            if not ckb_portals:
                print(f"Skipped; no portals to add.")
                return

            new_portals = ckb_portals
            new_template = '{{' + self.ckb_template_title + '|' + '|'.join(new_portals) + '}}'
            ckb_text = add_text(ckb_text, new_template, site=self.ckb_site)

        if ckb_text != ckb_page.text:
            # Generate links for added portals
            added_portal_links = [self.make_portal_link(portal) for portal in new_portals]

            # Generate the summary
            summary_prefix = self.get_tag_summary_prefix(len(new_portals))
            summary = self.opt.summary or f'بۆت: زیادکردنی {summary_prefix} {self.make_sentence(added_portal_links)}'

            # If the summary exceeds the limit (500 chars), simplify it
            if len(summary) > 499:
                summary = f'بۆت: زیادکردنی {summary_prefix} {self.make_sentence(new_portals)}'

            print(f"Added portals: {new_portals}")
            self.put_current(ckb_text, summary=summary)
        else:
            print(f"Skipped; no need to modify the article.")

def main(*args: str) -> None:
    """
    Process command line arguments and invoke bot.

    :param args: command line arguments
    """
    options = {}
    # Process global arguments to determine desired site
    local_args = pywikibot.handle_args(args)

    # This factory processes command line arguments for page generators
    gen_factory = pagegenerators.GeneratorFactory()
    local_args = gen_factory.handle_args(local_args)

    # Parse command line arguments
    for arg in local_args:
        arg, _, value = arg.partition(':')
        option = arg[1:]
        if option in ('summary'):
            if not value:
                pywikibot.input('Please enter a value for ' + arg)
            options[option] = value
        else:
            options[option] = True

    # Create a generator for pages
    gen = gen_factory.getCombinedGenerator(preload=True)

    # Create and run the bot
    if not pywikibot.bot.suggest_help(missing_generator=not gen):
        bot = PortalAdderBot(generator=gen, **options)
        bot.run()  # Runs the bot


if __name__ == '__main__':
    main()