#!/usr/bin/env python3
"""
A fully automated, multilingual bot for managing maintenance tags on Wikipedia
articles.

The bot operates by checking articles against a set of conditions to determine
if a maintenance tag should be added or removed. It only saves an edit if
at least one tag is added or removed, preventing purely cosmetic changes.

Operational Flow:
1.  Initialization: On startup, the bot performs a one-time data fetch from
    Wikidata for ~170 layout templates, tags and their redirects, displaying
    a progress bar. This data is cached for the duration of the run.
2.  Page Processing: The bot processes pages only within the article namespace,
    automatically skipping disambiguation pages.
3.  Editing Logic: Each article is parsed into a header, sections, and a
    footer. All edits are confined to the header and footer, leaving the main
    article content within the sections untouched.
4.  Tag Management: If multiple (2+) maintenance and cleanup tags are present,
    they are grouped into a {{Multiple issues}} block.
5.  Edit Summary and Save: A detailed, language-aware edit summary is generated
    in a style similar to the Twinkle gadget before the page is saved.

Configuration and Recommendations:
- All tag definitions, and internationalization (i18n) messages are managed
  in the `tag_data.py` file, NOT here.
- For full functionality, it is recommended that the target wiki has the
  following templates: {{Multiple issues}} and {{DATE}} templates, and
  the supported maintenance tags themselves.

Currently supported maintenance tags are:
* unreferenced
* one_source
* blp_unreferenced
* blp_one_source
* deadend
* orphan
* uncategorized

The following parameters are supported:

-always           The bot won't ask for confirmation when putting a page.

-reason:          Append custom text to the default summary.
                  Useful for mentioning discussion permanent links.

-summary:         Overwrite the default summary. Becareful, this is not recommended as it
                  disables the detailed, automatic summary generation.

Example:
--------

To check recently changed articles on the English Wikipedia and apply tags:

    python pwb.py tag -family:wikipedia -lang:en -recentchanges

&params;
"""
#
# (C) Pywikibot team, 2025
#
# Distributed under the terms of the MIT license.
#
from __future__ import annotations

import pywikibot
from pywikibot.comms import http
from pywikibot.textlib import extract_sections
from pywikibot import pagegenerators
from pywikibot.bot import (
    ConfigParserBot,
    ExistingPageBot,
    SingleSiteBot,
)
import re
import string
import sys

from tag_data import (
    TAG_DEFINITIONS, SUMMARY_MESSAGES, MULTIPLE_ISSUES_QID, LIVING_PEOPLE_CATEGORY_QID,
    CITATION_TEMPLATES_QIDS, ALL_TAGS_BY_PRIORITY, LAYOUT_TEMPLATES_BY_PRIORITY,
)

TAGS_TITLES = {}

yes_no_mapping = {True: "Yes", False: "No"}

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {'&params;': pagegenerators.parameterHelp}  # noqa: N816

class TagBot(
    SingleSiteBot,  # A bot only working on one site
    ConfigParserBot,  # A bot which reads options from scripts.ini setting file
    ExistingPageBot,  # CurrentPageBot which only treats existing pages
):

    use_redirects = False  # treats non-redirects only

    update_options = {
        'reason': None,  # append custom text to the default summary
        'summary': None, # overwrite the default summary
    }

    # =========================================================================
    # Core Logic (Main Methods)
    # =========================================================================

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        pywikibot.info("Initializing bot: Fetching and caching template data...")

        # Compile a master list of all QIDs to fetch.
        tag_qids = list(ALL_TAGS_BY_PRIORITY.values())
        all_qids = list(set(tag_qids + CITATION_TEMPLATES_QIDS +
                            LAYOUT_TEMPLATES_BY_PRIORITY + [MULTIPLE_ISSUES_QID] +
                            [LIVING_PEOPLE_CATEGORY_QID]))
        
        # Fetch all titles from Wikidata in a single, efficient API call.
        all_titles = self._fetch_titles_from_wikidata(all_qids, self.site.code)

        # Distribute fetched titles into their respective groups.
        tags_titles = {name: all_titles.get(qid) for name, qid in ALL_TAGS_BY_PRIORITY.items()}
        citation_titles = [all_titles.get(qid) for qid in CITATION_TEMPLATES_QIDS if all_titles.get(qid)]
        layout_titles_by_qid = {qid: all_titles.get(qid) for qid in LAYOUT_TEMPLATES_BY_PRIORITY if all_titles.get(qid)}
        self.multiple_issues_title = all_titles.get(MULTIPLE_ISSUES_QID)
        # Store only the main title for the "Living people" category.
        self.living_people_cat_title = all_titles.get(LIVING_PEOPLE_CATEGORY_QID)

        # Warn if the "Living people" category could not be found.
        if not self.living_people_cat_title:
            pywikibot.warning(f"Could not find 'Living people' category for {self.site.code}wiki. BLP tagging will be disabled.")

        TAGS_TITLES[self.site.code] = {k: v for k, v in tags_titles.items() if v}
        self.tag_order = list(ALL_TAGS_BY_PRIORITY.keys())

        # Initialize the progress bar with a more readable calculation.
        total_items = (len(tags_titles) + len(citation_titles) +
                    len(layout_titles_by_qid) + 1)  # +1 for {{Multiple issues}}
        processed_items = 0

        # Fetch redirects for each group of templates.
        # Maintenance Tags
        self.tag_redirects = {}
        for name, title in tags_titles.items():
            redirects, processed_items = self._fetch_redirects_with_progress(
                [title], processed_items, total_items, "Fetching tag redirects")
            self.tag_redirects[name] = redirects

        # Fetch redirects for other template groups.
        self.mi_templates, processed_items = self._fetch_redirects_with_progress(
            [self.multiple_issues_title], processed_items, total_items, "Fetching {{Multiple issues}} redirects")

        all_citation_redirects, processed_items = self._fetch_redirects_with_progress(
            citation_titles, processed_items, total_items, "Fetching citation redirects")

        # Layout Templates (passed to _process_layout_templates)
        self.layout_templates_by_qid, processed_items = self._process_layout_templates(layout_titles_by_qid, processed_items, total_items)

        # Compile final regex patterns from the fetched redirect lists.
        if self.mi_templates:
            self.mi_templates_pattern = '|'.join(self.case_insensitive_first_letter(t) for t in self.mi_templates)
        else:
            self.mi_templates_pattern = None
            pywikibot.warning(f"Could not find {{Multiple issues}} template for {self.site.code}wiki. Tag wrapping logic will be disabled.")

        if all_citation_redirects:
            pattern = '|'.join(self.case_insensitive_first_letter(t) for t in set(all_citation_redirects))
            # Compile a regex to find any citation template in the text.
            self.citation_templates_regex = re.compile(
                r'\{\{\s*(' + pattern + r')(?:\s*\|.*?)?\}\}', re.IGNORECASE | re.DOTALL)
        else:
            self.citation_templates_regex = None

        # Create a reverse mapping from redirect to canonical tag name (canonical names themselves included).
        self.redirect_to_canonical = {r.lower(): can for can, red_list in self.tag_redirects.items() for r in red_list}

        # Prepare language-specific summary messages.
        self.summary_msgs = SUMMARY_MESSAGES['en'].copy()
        self.summary_msgs.update(SUMMARY_MESSAGES.get(self.site.code, {}))

        # Clear the progress bar line.
        sys.stdout.write('\n')
        pywikibot.info("Initialization complete. Starting page processing...")

    def treat_page(self) -> None:
        """Load the given page, do some changes, and save it."""
        if not self.is_page_eligible_for_edit(self.current_page):
            return

        # Analyze the page to gather necessary data for tag conditions.
        is_biography = self.is_blp(self.current_page)
        total_refs, refs_in_tags, refs_no_tags = self.count_references(self.current_page.text)
        num_links = self.count_internal_links(self.current_page)
        is_orphan_page = self.is_orphan(self.current_page)
        num_categories = self.count_visible_categories(self.current_page)

        # Log the analysis results.
        pywikibot.info('- Page Analysis:')
        pywikibot.info(f"{'    - Is BLP:':<25}{yes_no_mapping[is_biography]}")
        pywikibot.info(f"{'    - Is Orphan:':<25}{yes_no_mapping[is_orphan_page]}")
        pywikibot.info(f"{'    - Internal Links:':<25}{num_links}")
        pywikibot.info(f"{'    - References:':<25}{total_refs} ({refs_in_tags} with <ref> tags, {refs_no_tags} without <ref> tags)")
        pywikibot.info(f"{'    - Categories:':<25}{num_categories}")
        pywikibot.info('-' * 20)
        
        # Prepare lists to track tags to add or remove.
        tags_to_add = []
        tags_to_remove = []

        # Define the checks to run along with their condition functions and parameters.
        checks_to_run = [
            ('blp_unreferenced', self._blp_unreferenced_conditions, is_biography, total_refs),
            ('unreferenced', self._unreferenced_conditions, is_biography, total_refs),
            ('blp_one_source', self._blp_one_source_conditions, is_biography, total_refs),
            ('one_source', self._one_source_conditions, is_biography, total_refs),
            ('deadend', self._deadend_conditions, num_links),
            ('orphan', self._orphan_conditions, is_orphan_page),
            ('uncategorized', self._uncategorized_conditions, num_categories),
        ]

        for tag_name, condition_func, *args in checks_to_run:
            action, has_tag = self._check_tag(tag_name, condition_func, tags_to_add, tags_to_remove, *args)
            
            # Log the result in a padded format for better readability.
            padded_check = f'- Checking [{tag_name}]...'.ljust(35)

            if has_tag is not None:
                exists_str = f"Tag exists: {yes_no_mapping[has_tag]:<3}"  # Pad "No" to align output
                pywikibot.info(f'{padded_check}{exists_str} | Action: {action}')
            else: # Handles CONFIG_MISSING or TEMPLATE_NOT_FOUND
                pywikibot.info(f'{padded_check}Status: {action}')

        self.edit_page(self.current_page, tags_to_add, tags_to_remove)

    def edit_page(self, page, tags_to_add, tags_to_remove):
        # If there's no reason to edit, do nothing.
        if not tags_to_add and not tags_to_remove:
            pywikibot.info(f'No changes were needed on {page.title()}')
            return

        oldtext = page.text
        newtext = oldtext

        # Perform all removals on the full text first.
        for tag in set(tags_to_remove):
            pattern = r"\{\{\s*" + self.case_insensitive_first_letter(tag) + r"\s*\|?[^}]*?\}\}\n?"
            newtext = re.sub(pattern, "", newtext, flags=re.IGNORECASE)

        # Separate the MODIFIED text into parts.
        page_parts = extract_sections(newtext, self.site)
        header = page_parts.header
        sections = "".join(s.title + s.content for s in page_parts.sections)
        footer = page_parts.footer

        # Consolidate all existing top-level maintenance tags.
        all_top_tags_as_text = []
        mi_existed = False
        mi_opening, mi_closing = '', ''

        # Only run the wrapping logic if the {{Multiple issues}} template exists on the wiki.
        if self.mi_templates_pattern:

            # A robust regex to find {{mi}} and safely separate its components.
            # It handles named parameters (e.g., |section=yes) before or after the tag content.
            # It also handles VisualEditor's explicit |1= for the tag content.
            # Group 1 (opening): `{{Multiple issues|section=yes|` or `{{Multiple issues|1=`
            # Group 2 (content): The maintenance tags themselves
            # Group 3 (closing): `|collapsed=yes}}`
            mi_template_regex = (
                r"(\{\{(?:" + self.mi_templates_pattern + r")\s*"  # Start of template
                r"(?:\|(?:(?!1=)[^=}|]+=[^|}]*))*\s*\|(?:1=)?\s*)"  # Named params before & pipe
                r"((?:\{\{.*?\}\}\s*)*?)"  # Group 2: The actual tags (non-greedy)
                r"(\s*(?:\|[^=}|]+=[^|}]*)*\}\})"  # Group 3: Named params after & close
            )
            
            if mi_match := re.search(mi_template_regex, header, re.DOTALL | re.IGNORECASE):
                mi_existed = True
                mi_opening, content, mi_closing = mi_match.groups()
                tags_inside_mi = re.findall(r'\{\{.*?\}\}', content, re.DOTALL)
                all_top_tags_as_text.extend(t.strip() for t in tags_inside_mi)
                header = header.replace(mi_match.group(0), '', 1)

        # Gather all standalone maintenance tags, removing them from the header.
        for tag_name in self.tag_redirects:
            # The 'uncategorized' tag is handled separately at the bottom of the page.
            if tag_name == 'uncategorized':
                continue
            
            regex = self._create_tag_regex(tag_name)
            if regex and (matches := list(regex.finditer(header))):
                all_top_tags_as_text.extend(m.group(0) for m in matches)
                header = regex.sub('', header)

        # Prepare new tags to be added, ensuring no duplicates.
        existing_tag_names = set()
        template_name_re = re.compile(r'{{\s*([^|}]+)')
        for tag_text in all_top_tags_as_text:
            if match := template_name_re.match(tag_text):
                # Get the template name (e.g., "Orphaned") and look it up.
                name = match.group(1).strip().lower()
                if name in self.redirect_to_canonical:
                    existing_tag_names.add(self.redirect_to_canonical[name])

        bottom_tags = ""
        for tag in tags_to_add:
            # This check is now extremely fast and does not use regex.
            if tag not in existing_tag_names:
                tag_def = self.get_tag_config(tag)
                if tag_def.get('addable'):
                    tag_template = TAGS_TITLES[self.site.code][tag]
                    params = tag_def.get('params', '')
                    added_content = f"{{{{{tag_template}{params}}}}}"
                    if tag == "uncategorized":
                        bottom_tags += f"\n{added_content}"
                    else:
                        all_top_tags_as_text.append(added_content)

        # Rebuild the header with the consolidated and sorted tags.
        sorted_templates_str, remaining_header = self.handle_templates_above_top_tags(header)

        final_tags_block = ""

        # Only sort the list if there is more than one tag.
        if len(all_top_tags_as_text) > 1:
            try:
                all_top_tags_as_text.sort(key=self._get_tag_sort_key)
            except Exception as e:
                pywikibot.warning(f"Could not sort tags: {e}. Proceeding with unsorted tags.")

        # Decide whether to wrap the now-sorted list in {{Multiple issues}}.
        if len(all_top_tags_as_text) > 1 and self.multiple_issues_title:
            mi_inner_content = "\n".join(all_top_tags_as_text)

            if mi_existed:
                # Rebuild the template using its original opening/closing parts to preserve parameters.
                final_tags_block = f"{mi_opening}{mi_inner_content}\n{mi_closing.lstrip()}\n"
            else:
                # Create a new template using the canonical title.
                final_tags_block = f"{{{{{self.multiple_issues_title}|\n{mi_inner_content}\n}}}}\n"
        elif all_top_tags_as_text:
            # If there's only one tag, place it as a standalone template.
            final_tags_block = "\n".join(all_top_tags_as_text) + "\n"

        header = sorted_templates_str + final_tags_block + remaining_header.lstrip('\n')
        # pywikibot.info(f"Header after modification:\n{header}")

        # Add bottom tags and finalize the page text.
        footer += bottom_tags
        newtext = header + sections + footer

        # Generate the edit summary and save the page.
        edit_summary = self.generate_edit_summary(tags_to_add, tags_to_remove)
        self.userPut(page, oldtext, newtext, summary=edit_summary)

    # =========================================================================
    # Condition Logic
    # =========================================================================

    def _check_tag(self, tag_name, condition_func, tags_to_add, tags_to_remove, *args):
        """
        Generic handler for checking a tag. It decides on an action and
        updates the add/remove lists. Returns the action taken and if the tag existed.
        """
        tag_conf = self.get_tag_config(tag_name)
        if not tag_conf:
            return "CONFIG_MISSING", None

        regex = self._create_tag_regex(tag_name)
        if not regex:
            return "TEMPLATE_NOT_FOUND", None

        has_tag = bool(regex.search(self.current_page.text))
        should_add, should_remove = condition_func(has_tag, *args)
        
        action = "NONE"
        if should_add and tag_conf.get("addable"):
            tags_to_add.append(tag_name)
            action = "ADD"
        elif should_remove and tag_conf.get("removable"):
            tags_to_remove.extend(self.tag_redirects[tag_name])
            action = "REMOVE"
        
        return action, has_tag

    def _unreferenced_conditions(self, has_tag, is_biography, num_refs):
        """Condition logic for the 'unreferenced' tag (non-BLP pages)."""
        should_have_tag = (num_refs == 0 and not is_biography)
        return (not has_tag and should_have_tag), (has_tag and not should_have_tag)
    
    def _blp_unreferenced_conditions(self, has_tag, is_biography, num_refs):
        """Condition logic for the 'BLP unreferenced' tag."""
        should_have_tag = (num_refs == 0 and is_biography)
        return (not has_tag and should_have_tag), (has_tag and not should_have_tag)

    def _one_source_conditions(self, has_tag, is_biography, num_refs):
        """Condition logic for the 'one source' tag (non-BLP pages)."""
        should_have_tag = (num_refs == 1 and not is_biography)
        return (not has_tag and should_have_tag), (has_tag and not should_have_tag)

    def _blp_one_source_conditions(self, has_tag, is_biography, num_refs):
        """Condition logic for the 'BLP one source' tag."""
        should_have_tag = (num_refs == 1 and is_biography)
        return (not has_tag and should_have_tag), (has_tag and not should_have_tag)

    def _deadend_conditions(self, has_tag, num_links):
        """Condition logic for the 'deadend' tag."""
        return (not has_tag and num_links == 0), (has_tag and num_links != 0)

    def _orphan_conditions(self, has_tag, is_orphan_page):
        """Condition logic for the 'orphan' tag."""
        return (not has_tag and is_orphan_page), (has_tag and not is_orphan_page)

    def _uncategorized_conditions(self, has_tag, num_cats):
        """Condition logic for the 'uncategorized' tag."""
        return (not has_tag and num_cats == 0), (has_tag and num_cats != 0)
    
    # =========================================================================
    # Data Analysis Helpers (Counters & Checkers)
    # =========================================================================
    
    def is_blp(self, page):
        """
        Check if the page is a biography of a living person by checking for
        the canonical 'Living people' category.
        """
        # This safety check prevents a crash if the BLP category was not found.
        if not self.living_people_cat_title:
            return False

        blp_cat_lower = self.living_people_cat_title.lower()
        return any(cat.title(with_ns=False).lower() == blp_cat_lower
                for cat in page.categories())
    
    def is_orphan(self, page):
        """Check if the page has no backlinks from other articles."""
        return len(list(page.backlinks(namespaces=0, filter_redirects=False))) == 0
    
    def count_internal_links(self, page):
        """Count the number of internal links on the page."""
        return len(list(page.linkedPages(namespaces=0)))

    def count_references(self, text):
        """
        Count references by counting <ref> tags and citation templates that
        are not already inside a <ref> tag.
        """
        # Count all unique, content-filled <ref> tags.
        # Match <ref>...</ref> or <ref name="...">...</ref>, but NOT self-closing <ref ... />
        refs = re.findall(r"<ref(?: name=\"[^\"]*\")?\s*>.*?</ref>", text, re.DOTALL)
        num_refs = len(refs)

        num_citations = 0
        if self.citation_templates_regex:
            # Create a clean version of the text by removing all <ref> blocks,
            # including self-closing ones like <ref name="..."/>
            ref_block_regex = r"<ref(?:.|\n)*?</ref>|<ref[^>]*?/>"
            text_without_refs = re.sub(ref_block_regex, "", text, flags=re.IGNORECASE)
            
            # Now, safely search for citation templates without <ref> tags in the clean text.
            num_citations = len(self.citation_templates_regex.findall(text_without_refs))

        total_sources = num_refs + num_citations
        return total_sources, num_refs, num_citations

    def count_visible_categories(self, page):
        """Count the number of non-hidden categories on the page."""
        non_hidden_categories = [cat for cat in page.categories() if not cat.isHiddenCategory()]
        num_categories = len(non_hidden_categories)
        return num_categories

    # =========================================================================
    # Wikitext & Sorting Helpers
    # =========================================================================

    def handle_templates_above_top_tags(self, header):
        """Identify and sort templates above top tags based on predefined QID order."""
        # Find and extract templates above tags one by one using their patterns
        templates_above_tags = []
        for qid, pattern in self.qid_patterns.items():
            matches = list(re.finditer(pattern, header))
            for match in matches:
                template = match.group()
                templates_above_tags.append((qid, template))

        # Sort the list of templates above tags based on the order of QIDs
        templates_above_tags.sort(key=lambda item: list(self.layout_templates_by_qid.keys()).index(item[0]))

        # Initialize remaining header with original header because we need a new variable to get
        # remaining lines below added top tags and can not work with header directly
        remaining_header = header

        # Remove sorted templates from header
        for qid, template in templates_above_tags:
            remaining_header = remaining_header.replace(template, '') # Remove all occurrences of above templates

        # Construct the string of sorted templates
        sorted_templates = [item[1] for item in templates_above_tags]
        sorted_templates_str = ''.join(sorted_templates) if sorted_templates else ''

        # Return both sorted templates string and remaining header
        return sorted_templates_str, remaining_header
    
    def _create_tag_regex(self, tag_name: str) -> re.Pattern | None:
        """Create a compiled regex to find a tag and its redirects."""
        all_titles = self.tag_redirects.get(tag_name)
        if not all_titles:
            return None
        
        pattern_str = r"\{\{(" + "|".join(
            self.case_insensitive_first_letter(tag) for tag in all_titles
        ) + r")(?:\s*\|.*?)*?\s*\}\}"
        return re.compile(pattern_str, re.IGNORECASE)

    def _get_tag_sort_key(self, tag_wikitext):
        """Find the index of a tag's canonical name in the master sort list."""
        for index, canonical_name in enumerate(self.tag_order):
            regex = self._create_tag_regex(canonical_name)
            # If a regex exists and it matches, return its priority (index).
            if regex and regex.search(tag_wikitext):
                return index
        # If the tag is not in our list, send it to the end.
        return len(self.tag_order)
    
    # =========================================================================
    # Edit Summary Generation
    # =========================================================================
    
    def generate_edit_summary(self, tags_to_add, tags_to_remove):
        """Generate a language-aware edit summary."""
        # Use the pre-computed message dictionary prepared during initialization.
        msgs = self.summary_msgs
        
        # Ensure unique tag names for removal based on canonical names.
        unique_tags_to_remove = {
            self.redirect_to_canonical.get(tag_title.lower())
            for tag_title in tags_to_remove
        }
        # Filter out any None values in case a removed tag wasn't a known maintenance tag.
        unique_tags_to_remove = {name for name in unique_tags_to_remove if name}
        
        summary_parts = []
        if tags_to_add:
            links = [self.make_template_link(TAGS_TITLES[self.site.code][t], msgs) for t in tags_to_add]
            prefix = msgs['tag'] if len(links) == 1 else msgs['tags']
            summary_parts.append(f"{msgs['adding']} {prefix} {self.make_sentence(links, msgs)}")
            
        if unique_tags_to_remove:
            links = [self.make_template_link(TAGS_TITLES[self.site.code][t], msgs) for t in unique_tags_to_remove]
            prefix = msgs['tag'] if len(links) == 1 else msgs['tags']
            summary_parts.append(f"{msgs['removing']} {prefix} {self.make_sentence(links, msgs)}")
    
        edit_summary = msgs['separator'].join(summary_parts)
    
        # Handle command-line summary options
        if self.opt.reason and self.opt.summary:
            pywikibot.error(
                "Invalid summary options. Use either -reason or -summary, not both.")
            sys.exit(1)
        elif self.opt.summary:
            return self.opt.summary
        elif self.opt.reason:
            edit_summary += f': {self.opt.reason}'
    
        # Add the bot prefix only if a summary was actually generated.
        if edit_summary:
            edit_summary = msgs['bot_prefix'] + edit_summary
    
        # Shorten summary if it exceeds the character limit
        if len(edit_summary) > 499:
            edit_summary = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', edit_summary)
            
        return edit_summary
    
    def make_sentence(self, items: list[str], msgs: dict) -> str:
        """Create a grammatically correct list string."""
        if not items:
            return ''
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]}{msgs['and']}{items[1]}"
        return msgs['comma_separator'].join(items[:-1]) + f"{msgs['and']}{items[-1]}"
    
    def make_template_link(self, tag: str, msgs: dict) -> str:
        """Create a formatted link to a template for the summary."""
        if '|' in tag:
            tag = tag.split('|', 1)[0]
        
        ns = msgs['template_ns']
        return f'{{{{[[{ns}:{tag}|{tag}]]}}}}'
    
    # =========================================================================
    # API & Setup Helpers
    # =========================================================================
    
    def _fetch_titles_from_wikidata(self, qids, language):
        """
        Fetch sitelinks for a list of Wikidata QIDs in a single API call.
        Returns a dictionary mapping QID to page title.
        """
        if not qids:
            return {}
            
        url = (f"https://www.wikidata.org/w/api.php?"
               f"action=wbgetentities&ids={'|'.join(qids)}&props=sitelinks"
               f"&languages={language}&format=json")
        try:
            response = http.fetch(url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            pywikibot.error(f"Could not fetch titles from Wikidata: {e}")
            return {}

        results = {}
        site_key = f"{language}wiki"
        entities = data.get('entities', {})
        for qid, entity_data in entities.items():
            sitelinks = entity_data.get('sitelinks', {})
            if site_key in sitelinks:
                title = sitelinks[site_key]['title']
                results[qid] = title.split(':', 1)[-1]  # Remove namespace
        return results
    
    def _get_template_redirects(self, site, template_title):
            """Get a list of redirect titles for a given template."""
            page = pywikibot.Page(site, template_title, ns=10)
            redirects = page.redirects(filter_fragments=False, namespaces=10)
            return [redirect.title(with_ns=False) for redirect in redirects]

    def _fetch_redirects_with_progress(self, titles, processed_items, total, status):
        """
        Generic helper to fetch all redirects for a list of template titles
        and update the progress bar. Returns a flat list of all unique titles
        (originals + redirects) and the updated progress count.
        """
        all_redirects = []
        for title in titles:
            if title:  # Ensure title is not None
                redirects = self._get_template_redirects(self.site, title)
                all_redirects.extend([title] + redirects)
            processed_items += 1
            self._update_progress(processed_items, total, status)
        return list(set(all_redirects)), processed_items

    def _process_layout_templates(self, layout_titles_by_qid, processed_items, total_items):
        """
        Takes a pre-fetched dictionary of QIDs to layout titles, fetches
        their redirects, and builds the regex patterns needed for sorting.
        """
        results = {}
        for qid, title in layout_titles_by_qid.items():
            redirects, processed_items = self._fetch_redirects_with_progress(
                [title], processed_items, total_items, "Fetching layout redirects")
            results[qid] = redirects

        # Generate the pattern for each QID.
        patterns = {}
        for qid, templates in results.items():
            template_titles = "|".join(self.case_insensitive_first_letter(template) for template in templates)
            pattern = r"(?ms)\{\{(?:" + template_titles + r")\s*\|?(?:\{\{.*?\}\}|[^\{\}])*\}\}\n?"
            patterns[qid] = pattern

        self.qid_patterns = patterns
        return results, processed_items
    
    # =========================================================================
    # Utility Helpers
    # =========================================================================
    
    def get_tag_config(self, tag_name):
        """Get the effective tag configuration by merging site-specific overrides
        with the default configuration from the unified TAG_DEFINITIONS."""
        # Start with a copy of the default settings for the tag
        defaults = TAG_DEFINITIONS.get('default', {}).get(tag_name, {})
        config = defaults.copy()

        # Get the dictionary of overrides for the current site's language
        site_overrides = TAG_DEFINITIONS.get(self.site.code, {})

        # If there are specific overrides for this tag on this site, apply them
        if tag_name in site_overrides:
            config.update(site_overrides[tag_name])
            
        return config
    
    def is_page_eligible_for_edit(self, page):
        if page.namespace() != 0:
            pywikibot.info("Skipping page in non-article namespace.")
            return False
        
        if page.isDisambig():
            pywikibot.info(f'Skipping disambiguation page: {page.title()}')
            return False
        
        return True

    def case_insensitive_first_letter(self, tag):
        """Return a regex pattern for the tag with case-insensitive first letter."""
        if tag and tag[0] in string.ascii_letters:
            return "[" + tag[0].upper() + tag[0].lower() + "]" + re.escape(tag[1:])
        else:
            return re.escape(tag)
        
    def _update_progress(self, count, total, status=''):
        """Display a simple text-based progress bar."""
        bar_len = 40
        filled_len = int(bar_len * count / total)

        # Use integer percentage for a cleaner look.
        percents = int(100 * count / total)
        bar = '=' * filled_len + '-' * (bar_len - filled_len)

        # Build the output string first.
        output_str = f'[{bar}] {percents:3}% {status}...'
        
        # Pad to fixed width (e.g. 100) to overwrite old text, then return cursor.
        sys.stdout.write(output_str.ljust(100) + '\r')
        sys.stdout.flush()

def main(*args: str) -> None:
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    :param args: command line arguments
    """
    options = {}
    # Process global arguments to determine desired site
    local_args = pywikibot.handle_args(args)

    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    gen_factory = pagegenerators.GeneratorFactory()

    # Process pagegenerators arguments
    local_args = gen_factory.handle_args(local_args)

    # Parse your own command line arguments
    for arg in local_args:
        arg, _, value = arg.partition(':')
        option = arg[1:]
        if option in ('summary', 'reason'):
            if not value:
                pywikibot.input('Please enter a value for ' + arg)
            options[option] = value
        # take the remaining options as booleans.
        # You will get a hint if they aren't pre-defined in your bot class
        else:
            options[option] = True

    # The preloading option is responsible for downloading multiple
    # pages from the wiki simultaneously.
    gen = gen_factory.getCombinedGenerator(preload=True)

    # check if further help is needed
    if not pywikibot.bot.suggest_help(missing_generator=not gen):
        # pass generator and private options to the bot
        bot = TagBot(generator=gen, **options)
        bot.run()  # guess what it does

if __name__ == '__main__':
    main()
