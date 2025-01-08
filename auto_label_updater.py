#!/usr/bin/env python3
"""
A Pywikibot script to add missing, update outdated, and remove unnecessary ckbwiki labels
on Wikidata items based on ckb Wikipedia page titles. The entire process is automated.

Parameters supported:
-always           The bot won't ask for confirmation when putting a page
"""

import re
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import ExistingPageBot, SingleSiteBot
from pywikibot.exceptions import NoPageError, Error

class CkbLabelUpdaterBot(SingleSiteBot, ExistingPageBot):
    """
    A bot to add missing, update outdated, or remove unnecessary ckbwiki labels 
    on Wikidata items based on ckb Wikipedia page titles. The entire process is automated.
    """

    use_redirects = False  # treats non-redirects only
    allowed_namespaces = {0, 4, 10, 12, 14, 100, 828}  # Set of allowed namespaces

    # Counters for write operations
    label_additions = 0
    label_updates = 0
    label_deletions = 0

    def treat_page(self) -> None:
        """Process each page, check its Wikidata item, and do proper action for the ckb label if necessary."""
        if self.current_page.namespace() not in self.allowed_namespaces:
            pywikibot.output(f"Skipping {self.current_page.title()} due to namespace restriction.")
            return

        page_title = self.current_page.title()

        # Only remove anything between parentheses if the page is in namespace 0 (main namespace)
        if self.current_page.namespace() == 0:
            cleaned_page_title = re.sub(r'\([^)]*\)', '', page_title).strip()
        else:
            cleaned_page_title = page_title

        # Load the corresponding Wikidata item
        try:
            item = pywikibot.ItemPage.fromPage(self.current_page)
            item.get()  # Fetch the data from Wikidata

            # Get the current labels
            ckb_label = item.labels.get('ckb')
            mul_label = item.labels.get('mul')

            action = None

            # If mul_label exists and ckb_label is the same as mul_label, remove the ckb_label
            if mul_label and ckb_label == mul_label:
                summary = f'Removing ckb label because it matches the default (mul) label; see [[Help:Default values for labels and aliases|here]]'
                print(f"Removing ckb label for '{page_title}' because it matches the mul label.")
                action = 'remove'
                
            # If ckb_label has any value
            elif ckb_label:
                # And if the ckb label value was not the same as cleaned page title, update it
                if ckb_label != cleaned_page_title:
                    summary = f'Updating label from "{ckb_label}" to "{cleaned_page_title}"'
                    print(f"Updating label from '{ckb_label}' to '{cleaned_page_title}'.")
                    action = 'update'
                else:
                    pywikibot.output(f"Skipping {cleaned_page_title}: ckb label is already up-to-date.")
                    return
            # If the ckb_label is missing/empty
            elif cleaned_page_title != mul_label:
                summary = f'Adding missing label "{cleaned_page_title}" for "{page_title}"'
                print(f"Adding missing label '{cleaned_page_title}' for '{page_title}'.")
                action = 'add'
            else:
                pywikibot.output(f"Skipping {cleaned_page_title}: ckb label doesn't need to be added; default mul label is provided.")
                return
            
            # Confirm the action with the user before applying the change
            if action and self.user_confirm(f"Do you want to {action} the ckb label for '{page_title}'?"):
                if action == 'remove':
                    item.editLabels(labels={'ckb': ''}, summary=summary)
                    self.label_deletions += 1
                elif action == 'update':
                    item.editLabels(labels={'ckb': cleaned_page_title}, summary=summary)
                    self.label_updates += 1
                elif action == 'add':
                    item.editLabels(labels={'ckb': cleaned_page_title}, summary=summary)
                    self.label_additions += 1

        except NoPageError:
            pywikibot.output(f"Page {page_title} has no corresponding Wikidata item. Skipping.")
        except Error as e:
            pywikibot.output(f"An error occurred while processing {page_title}: {e}")

    def show_statistics(self) -> None:
        """Print statistics of write operations."""
        total_write_operations = self.label_additions + self.label_updates + self.label_deletions
        print("\nWrite Operations Statistics:")
        print(f"Labels added: {self.label_additions}")
        print(f"Labels updated: {self.label_updates}")
        print(f"Labels deleted: {self.label_deletions}")
        print(f"Total write operations: {total_write_operations}\n\n")

def main(*args: str) -> None:
    """
    Process command line arguments and invoke bot.
    """
    local_args = pywikibot.handle_args(args)

    # This factory processes command line arguments for page generators
    gen_factory = pagegenerators.GeneratorFactory()
    gen_factory.handle_args(local_args)

    options = {}
    if '-always' in local_args:
        options['always'] = True

    # Create a generator for pages
    gen = gen_factory.getCombinedGenerator(preload=True)

    # Create and run the bot
    if not pywikibot.bot.suggest_help(missing_generator=not gen):
        bot = CkbLabelUpdaterBot(generator=gen, **options)
        bot.run()
        bot.show_statistics()

if __name__ == '__main__':
    main()
