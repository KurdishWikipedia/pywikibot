#!/usr/bin/env python3
"""
A bot script for removing spam references and optionally adding {{citation needed}}.
For the search, it is a good idea to use '-weblink' argument which is a part of pywikibot itself.

Parameters supported:
-always         The bot won't ask for confirmation when putting a page.
                We don't recommend this; use it carefully.
-replace:       Replace removed spam references with {{citation needed}}
                (default is to replace with {{citation needed}}).
-reason:        Set a required reason (appended to the default summary). 
                Useful for mentioning discussion links.
-domain:        Specify the spam domain to remove (required).

Usage:
python pwb.py spam_remover.py -family:wikipedia -lang:ckb -weblink:https://example.com -domain:example.com -reason
"""

import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
import re

class SpamRemoverBot(
    SingleSiteBot,  # A bot only working on one site
    ConfigParserBot,  # A bot which reads options from scripts.ini setting file
    ExistingPageBot,  # CurrentPageBot which only treats existing pages
):
    """
    A bot to remove spam references and optionally add {{citation needed}}.
    """

    use_redirects = False  # treats non-redirects only

    update_options = {
        'reason': None,  # reason (required)
        'always': False,  # confirm changes or not
        'replace': '{{subst:ژێدەر پێویستە}}',  # default to replacing with {{citation needed}}
        'domain': None,  # spam domain must be provided
    }

    def treat_page(self) -> None:
        """Load the given page, remove spam references, and save it."""
        text = self.current_page.text

        # Get the spam domain and replacement text from the options
        spam_domain = self.opt.domain
        replace_text = self.opt.replace
        summary_reason = self.opt.reason

        # Define a combined pattern to match unnamed and named references with optional name capture
        refs_pattern = re.compile(
            r'<ref(?:\s+name="([^"]+)")?[^>]*>[^<]*?' + re.escape(spam_domain) + r'[^<]*?</ref>',
            re.IGNORECASE | re.DOTALL
        )

        # Find all matches of the combined pattern
        matches = refs_pattern.findall(text)
        
        # Extract names from matches, if present
        named_refs = set(name for name in matches if name)

        # Create a pattern to match <ref name="NAME" /> where NAME is in the set of named_refs
        if named_refs:
            names_pattern = re.compile(r'<ref\s+name="(' + '|'.join(re.escape(name) for name in named_refs) + r')"[^>]*?/>', re.IGNORECASE)
            new_text = names_pattern.sub(replace_text, text)
        else:
            new_text = text

        # Replace all unnamed references containing the spam domain with the replacement text
        new_text = refs_pattern.sub(replace_text, new_text)

        # Also, remove lines with external links containing the spam domain
        external_link_pattern = re.compile(r'\*?.*?\[?.*?' + re.escape(spam_domain) + r'.*?\]?.*?\n+', re.IGNORECASE)
        new_text = external_link_pattern.sub('', new_text)

        # Check if the page text has changed
        if new_text != text:
            # Create a default summary mentioning the domain and replacement text
            default_summary = f"بۆت: لابردنی سەرچاوەکانی '{spam_domain}' و دانانی '{replace_text}' بەجێگەیان"
            summary = default_summary + "؛ " + summary_reason
            self.put_current(new_text, summary=summary)
        else:
            print("No changes made to the page.")


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

        if option in ('reason', 'domain'):
            if not value:
                pywikibot.error(f"The {arg} parameter requires a value.")
                return
            options[option] = value
        elif option == 'replace':
            options[option] = value
        else:
            options[option] = True

    # Ensure required parameters are provided
    if 'domain' not in options or not options['domain']:
        pywikibot.error("The -domain parameter is required.")
        return

    if 'reason' not in options or not options['reason']:
        pywikibot.error("The -reason parameter is required.")
        return

    # Create a generator for pages
    gen = gen_factory.getCombinedGenerator(preload=True)

    # Create and run the bot
    if not pywikibot.bot.suggest_help(missing_generator=not gen):
        bot = SpamRemoverBot(generator=gen, **options)
        bot.run()  # Runs the bot

if __name__ == '__main__':
    main()
