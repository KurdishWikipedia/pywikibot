#!/usr/bin/env python3
"""
A bot to update citation parameters based on a mapping page on Wikipedia.
Cite templates, parameter names and values are configured on the mapping page.
Mapping page link on ckbwiki: https://w.wiki/Cf74.

Parameters supported:
-always           The bot won't ask for confirmation when putting a page
-remove_empty:    Removes all empty parameters. Default: False
-summary:         Set the action summary message for the edit.

Tasks:
1.  update_parameter_names: updates old parameter names with a new one.
2.  remove_empty_parameters: removes empty parameters from citations.
3.  convert_numbered_parameter_values: using a list inside the function
    to convert their numbers such as: isbn, year, volume, page etc. values.
4.  fix_date_parameters: fix date formats for specific parameters only if they match predefined patterns.
5.  replace_invalid_values: replaces invalid values in parameters with valid values based on the mapping.
6.  remove_duplicate_parameters: removes duplicate parameters with the same value 
    keeping the last one in the citation template.
7.  fix_timestamp_mismatch: fixes timestamp mismatch for archive date based on archive URL.
8.  remove_wikimarkup_from_parameters: removes italic and bold markup from specific parameters' values.

Notes: Each function has it's own summary merging them all at the end.
"""

import re
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
    SingleSiteBot,
    ConfigParserBot,
    ExistingPageBot,
)
class CiteParamUpdaterBot(
    SingleSiteBot,
    ConfigParserBot,
    ExistingPageBot,
):
    """A bot to update citation parameters."""

    use_redirects = False

    update_options = {
        'summary': None,
        'always': False,
        'remove_empty': False,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.month_map = {
            'کانوونی دووەم': ['1', '01', 'Jan', 'January', '١', '٠١'],
            'شوبات': ['2', '02', 'Feb', 'February', '٢', '٠٢'],
            'ئازار': ['3', '03', 'Mar', 'March', '٣', '٠٣'],
            'نیسان': ['4', '04', 'Apr', 'April', '٤', '٠٤'],
            'ئایار': ['5', '05', 'May', '٥', '٠٥'],
            'حوزەیران': ['6', '06', 'Jun', 'June', '٦', '٠٦'],
            'تەممووز': ['7', '07', 'Jul', 'July', '٧', '٠٧'],
            'ئاب': ['8', '08', 'Aug', 'August', '٨', '٠٨'],
            'ئەیلوول': ['9', '09', 'Sep', 'September', '٩', '٠٩'],
            'تشرینی یەکەم': ['10', 'Oct', 'October', '١٠'],
            'تشرینی دووەم': ['11', 'Nov', 'November', '١١'],
            'کانوونی یەکەم': ['12', 'Dec', 'December', '١٢']
        }

        kurdish_months = list(self.month_map.keys())  # Get all Kurdish month names
        self.kurdish_months_pattern = '|'.join(map(re.escape, kurdish_months)) # Create a regex pattern for Kurdish month names
        
        self.season_map = {
            'spring': 'بەھار',
            'summer': 'ھاوین',
            'fall': 'پاییز',
            'winter': 'زستان'
        }

        # Initialize the edit_summary, mapping_dict, template_name_mapping, and invalid_values_mapping
        self.edit_summary = set()  # Use a set to store unique actions
        self.mapping_dict = {}
        self.template_name_mapping = {}
        self.invalid_values_mapping = {}

        # Check if the mapping page exists
        self.mapping_page_title = self.get_mapping_page_title()
        mapping_page = pywikibot.Page(pywikibot.Site(), self.mapping_page_title)

        if not mapping_page.exists():
            pywikibot.error(f'The mapping page "{self.mapping_page_title}" does not exist on {pywikibot.Site()}. Please check the script docs to create it and try again.')
            self.generator.close()
            return
        
        # Fetch the template and parameter mappings
        self.template_name_mapping = self.get_mapping_by_section("داڕێژەکان")
        self.mapping_dict = self.get_mapping_by_section("پارامەترەکان")

        self.invalid_values_mapping = self.get_invalid_values_mapping()  # Fetch invalid values mapping

    def get_mapping_page_title(self) -> str:
        """Return the title of the mapping page."""
        return 'بەکارھێنەر:AramBot/نوێکردنەوەی پارامەترەکانی سەرچاوەکان'
    
    def get_mapping_by_section(self, section_title: str) -> dict:
        """Fetch a mapping from the specified section of the page."""
        mapping_page = pywikibot.Page(pywikibot.Site(), self.mapping_page_title)
        mapping_text = mapping_page.text

        # Regex to locate the specified section
        section_re = re.compile(rf'===\s*{re.escape(section_title)}\s*===', re.IGNORECASE)
        # Regex to match the entire wikitable content
        wikitable_re = re.compile(r'{\|\s*class="wikitable".*?\|}', re.DOTALL)

        # Locate the specified section
        section_match = section_re.search(mapping_text)
        if not section_match:
            return {}

        # Extract the text following the section title
        section_start = section_match.end()
        section_content = mapping_text[section_start:]

        # Find the wikitable within this section
        wikitable_match = wikitable_re.search(section_content)
        if not wikitable_match:
            return {}

        # Extract the wikitable content
        table_content = wikitable_match.group(0).strip()

        # Parse the table rows to extract mappings
        mapping = {}
        for row in table_content.splitlines():
            if '||' in row:
                old_items_raw, new_item = [cell.strip() for cell in row.split('||')]
                old_items = [item.strip('|').strip() for item in old_items_raw.split('/')] # | url/URL || ناونیشان
                for old_item in old_items:
                    mapping[old_item] = new_item
        return mapping
    
    def update_parameter_names(self, template_content: str) -> str:
        """Update old parameter names to new ones within a given template content."""

        def replace_serial_param(match):
            """Helper function to replace numbered parameters with updated names, converting numbers if necessary."""
            # Extract the optional number from the regex match (e.g., '2' from 'first2').
            number = match.group(1)
            # Convert the extracted number to Indo-Arabic format using the helper function, if a number is present.
            converted_number = self.convert_to_indo_arabic_numbers(number) if number else ""
            # Replace the hash symbol ('#') in the new parameter name with the converted number (or leave it empty if no number).
            updated_param = new_param.replace('#', converted_number)
            # Return the updated parameter name formatted for use in the template (e.g., '|یەکەم٢=').
            return f"|{updated_param}="

        original_content = template_content  # Keep a copy of the original content

        # Loop through the mapping dictionary containing old and new parameter names.
        for old_param, new_param in self.mapping_dict.items():
            if '#' in old_param:
                # Create pattern by escaping the entire string and replacing the # with an 
                # optional digit capture (e.g., 'author', 'author#', author-link# or author#-link).
                param_pattern = re.escape(old_param).replace(r'\#', r'(\d*)')
                # Replace matching parameter names in the template content with the updated parameter names.
                # The `replace_serial_param` function handles the conversion and replacement.
                template_content = re.sub(rf'\|\s*{param_pattern}\s*=', replace_serial_param, template_content)
            else:
                # For parameters without a hash symbol, directly replace them with the new parameter name.
                template_content = re.sub(rf'\|\s*{re.escape(old_param)}\s*=', rf'|{new_param}=', template_content)

        # If the content has changed, generate an edit summary and return the updated content.
        if template_content != original_content:
            template_content = template_content.strip()
            self.generate_edit_summary("ناوی پارامەترە کۆنەکان نوێ کرایەوە")

        return template_content

    def remove_empty_parameters(self, template_content: str) -> str:
        """Remove parameters with empty values in the template content."""
        # Use a regex to match parameters with empty values (e.g., |param=) dynamically for any language
        empty_param_pattern = re.compile(r'\|\s*[^\|={}<>]+\s*=\s*(?=\||}}|$)', re.UNICODE)
        
        # Create a cleaned version of the content
        cleaned_content = empty_param_pattern.sub('', template_content)

        # Only generate the edit summary if modifications were made
        if cleaned_content != template_content:
            cleaned_content = cleaned_content.strip()  # Strip only if changes were made
            self.generate_edit_summary("پارامەترە واڵاکان لابران")
        
        return cleaned_content

    def get_invalid_values_mapping(self) -> dict:
        """Fetch invalid values mapping from the specified section of the mapping page."""
        mapping_page = pywikibot.Page(pywikibot.Site(), self.mapping_page_title)
        mapping_text = mapping_page.text

        # Regex to find the section with invalid values
        section_re = re.compile(r'===\s*نوێکردنەوەی نرخی پارامەترەکان\s*===.*?({\|.*?\|})', re.DOTALL)
        match = section_re.search(mapping_text)

        invalid_values_mapping = {}
        if match:
            wikitable_content = match.group(1)  # Get the content of the wikitable
            rows = wikitable_content.splitlines()

            for row in rows:
                # Match the rows of the wikitable
                if '||' in row:
                    columns = [cell.strip() for cell in row.split('||')]
                    if len(columns) >= 3:  # Ensure there are enough columns
                        parameter = columns[0].strip().lstrip('|').strip()  # Remove leading pipe and trim surrounding whitespace
                        invalid_values = columns[1].split('/')  # Split old values by '/'
                        valid_value = columns[2].strip()

                        # Create a mapping for the parameter
                        if parameter not in invalid_values_mapping:
                            invalid_values_mapping[parameter] = {}

                        for old_value in invalid_values:
                            invalid_values_mapping[parameter][old_value.strip()] = valid_value  # Map old to new value

        return invalid_values_mapping
    
    def replace_invalid_values(self, template_content: str) -> str:
        """Replace invalid values in parameters with valid values based on the mapping."""
        original_content = template_content  # Keep a copy of the original content
        
        # Loop through each parameter and its associated invalid-to-valid values mapping
        for parameter, values_mapping in self.invalid_values_mapping.items():
            # Loop through each old value and its corresponding new value
            for old_value, new_value in values_mapping.items():
                # Create a regex pattern to match the parameter with its old value
                pattern = rf'{parameter}\s*=\s*{re.escape(old_value)}'
                # Replace occurrences of the old value with the new value
                template_content = re.sub(pattern, f'{parameter}={new_value}', template_content)
        
        # Only generate the edit summary if modifications were made
        if template_content != original_content:
            template_content = template_content.strip()  # Strip only if changes were made
            self.generate_edit_summary("نرخی کۆنی پارامەترەکان نوێ کرایەوە")
            
        return template_content

    def remove_duplicate_parameters(self, template_content):
        """Remove duplicate parameters with the same value in the citation template."""
        parameters = {}
        lines = template_content.split('|')

        for line in lines[1:]:  # Start from the second item to keep the leading pipe
            
            # Check for the presence of '=' to identify key-value pairs
            if '=' in line:
                key = line.split('=', 1)[0].strip()  # Clean up the key

                # Check if this key is already associated with a value
                if key not in parameters:
                    # Store the entire line to preserve formatting
                    parameters[key] = line  # Store the line to keep original formatting
            else:
                # If there's no equal sign, simply keep the line as is (as a key without a value)
                parameters[line] = line  # Store it as a unique parameter with no value

        # Rebuild the template content using the original lines, preserving the leading pipe
        new_template_content = '|' + '|'.join(parameters[key] for key in parameters)

        # Only generate the edit summary if modifications were made
        if new_template_content != template_content:
            new_template_content = new_template_content.strip()  # Strip only if changes were made
            self.generate_edit_summary("پارامەترە دووبارەکان کە ھەمان نرخیان ھەیە لابران (بێجگە لە کۆتا دانە)")

        return new_template_content

    def convert_to_indo_arabic_numbers(self, number_string: str) -> str:
        """Convert numbers from Arabic numerals to Indo-Arabic numerals."""
        arabic_to_indo_arabic = {
            '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
            '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
        }
        return ''.join(arabic_to_indo_arabic.get(char, char) for char in number_string)

    def convert_numbered_parameter_values(self, template_content: str) -> str:
        """Convert numbers for specific parameters values to Indo-Arabic format."""
        parameters = [
             # List of parameters to process
            'display-authors', 'pmc', 'pmid', 'oclc', 'rfc',
            'ساڵ', 'بەرگ', 'ژمارە', 'ژپنک',
            'پ', 'پەڕە', 'پەڕەکان',
            'ژمارەی زنجیرە', 'وەرز',
            'دەقە', 'کات'
            ]
        modified = False  # Track if any modification is made

        for param in parameters:
            def replace_number(match):
                original_value = match.group(2).strip()
                converted_value = self.convert_to_indo_arabic_numbers(original_value)
                if converted_value != original_value:
                    nonlocal modified  # Mark that a modification has occurred
                    modified = True
                    return f"{match.group(1)}{converted_value}"
                return match.group(0)

            template_content = re.sub(
                rf'(\|\s*{param}\s*=\s*)([^|}}]+)',
                replace_number,
                template_content
            )

        if modified:
            template_content = template_content.strip()  # Strip only if changes were made
            self.generate_edit_summary("چاکسازیی ژمارەکان")

        return template_content

    def convert_month(self, month: str) -> str:
        """Convert month names or numbers to Kurdish month names."""
        for kurdish_name, representations in self.month_map.items():
            if month in representations:
                return kurdish_name
        return month  # Return the original month if no match is found

    def fix_date_format(self, date_str: str) -> str:
        """Convert date formats to the Kurdish format if they match specific patterns."""

        # Define regex patterns for month names and seasons
        month_pattern = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        season_pattern = r'(?:Spring|Summer|Fall|Winter)'

        # Combine patterns and extraction logic to avoid redundancy
        date_patterns = [

            # Season formats
            (rf'({season_pattern})ی?\s+([\d٠-٩]{{4}})', ('season', 'year')),  # Season YYYY (e.g., Spring 2019)
            (rf'({season_pattern})ی?\s+([\d٠-٩]{{4}})[–‒−―—\-]([\d٠-٩]{{4}})', ('season', 'year_start', 'year_end')),  # Season YYYY-YYYY (e.g., Spring 2019-2020)
            
            # Date formats with separators for day/month/year
            (r'([\d٠-٩]{4})[–‒−―—\-\\/‌]([\d٠-٩]{1,2})[–‒−―—\-\\/‌]([\d٠-٩]{1,2})', ('year', 'month', 'day')),  # Format: YYYY/MM/DD
            (r'([\d٠-٩]{1,2})[–‒−―—\-\\/‌]([\d٠-٩]{1,2})[–‒−―—\-\\/‌]([\d٠-٩]{4})', ('day', 'month', 'year')),  # Format: DD/MM/YYYY

            # English month name formats
            (rf'({month_pattern})\s+(\d{{1,2}}),\s+(\d{{4}})', ('month', 'day', 'year')),  # Format: Month DD, YYYY (e.g., January 15, 2020)
            (rf'(\d{{1,2}})\s+({month_pattern})\s+(\d{{4}})', ('day', 'month', 'year')),  # Format: DD Month YYYY (e.g., 15 January 2020)
            (rf'(\d{{4}})-({month_pattern})-(\d{{2}})', ('year', 'month', 'day')),  # Format: YYYY-Mon-DD (e.g., 2020-Jan-15)

            # Special formats
            (r'(\d{4})(\d{2})(\d{2})', ('year', 'month', 'day')),  # Format: YYYYMMDD (for fix_timestamp_mismatch function)
            (r'([\d٠-٩]{1,2})ی? (' + self.kurdish_months_pattern + r') ([\d٠-٩]{4})', ('day', 'month', 'year')),  # Kurdish format: Last chance to fix problems in Kurdish dates further.

            # Year-only formats
            (r'^([\d٠-٩]{4})$', ('year',)),  # Single year (e.g., 2009)
            (r'^([\d٠-٩]{4})[–‒−―—\-]([\d٠-٩]{4})$', ('year_start', 'year_end')),  # Year range (e.g., 2003-2004)

            # Month-Year combinations
            (rf'({month_pattern})\s+([\d٠-٩]{{4}})', ('month', 'year')),  # Format: Month YYYY (e.g., August 2019)
            (rf'({month_pattern})\s+([\d٠-٩]{{4}})[–‒−―—\-]({month_pattern})\s+([\d٠-٩]{{4}})', ('month_start', 'year_start', 'month_end', 'year_end')),  # Month YYYY - Month YYYY
            (rf'({month_pattern})[–‒−―—\-]({month_pattern})\s+([\d٠-٩]{{4}})', ('month_start', 'month_end', 'year'))  # Month-Month YYYY (e.g., January-March 2020)         
        ]

        for pattern, group_order in date_patterns:
            match = re.match(pattern, date_str, re.IGNORECASE)
            if match:
                groups = match.groups()
                extracted_values = {group_order[i]: groups[i] for i in range(len(groups))}

                # Hanlde season formats first    
                if 'season' in extracted_values:
                    season_key = extracted_values['season'].lower()
                    season = self.season_map.get(season_key)
                    if season is None:
                        return date_str  # Return original if season not found
                    if 'year_end' in extracted_values:  # Season YYYY-YYYY
                        year_start = self.convert_to_indo_arabic_numbers(extracted_values['year_start'])
                        year_end = self.convert_to_indo_arabic_numbers(extracted_values['year_end'])
                        return f"{season}ی {year_start}–{year_end}"
                    else:  # Season YYYY
                        year = self.convert_to_indo_arabic_numbers(extracted_values['year'])
                        return f"{season}ی {year}"

                # Handle different date format cases
                if 'year_start' in extracted_values:  # Date range cases
                    year_start = self.convert_to_indo_arabic_numbers(extracted_values['year_start'])
                    year_end = self.convert_to_indo_arabic_numbers(extracted_values['year_end'])
                    
                    if 'month_start' in extracted_values:  # Month YYYY - Month YYYY
                        # Convert both month names to Kurdish
                        month_start = self.convert_month(extracted_values['month_start'])
                        month_end = self.convert_month(extracted_values['month_end'])
                        return f"{month_start}ی {year_start} – {month_end}ی {year_end}"
                    
                    return f"{year_start}–{year_end}"  # Simple year range
                
                elif 'month_start' in extracted_values:  # Month-Month YYYY
                    # Convert both month names to Kurdish
                    month_start = self.convert_month(extracted_values['month_start'])
                    month_end = self.convert_month(extracted_values['month_end'])
                    year = self.convert_to_indo_arabic_numbers(extracted_values['year'])
                    return f"{month_start}–{month_end}ی {year}"

                elif 'month' in extracted_values and 'year' in extracted_values and 'day' not in extracted_values:
                    # Month YYYY format
                    month_name = self.convert_month(extracted_values['month'])
                    indo_arabic_year = self.convert_to_indo_arabic_numbers(extracted_values['year'])
                    return f"{month_name}ی {indo_arabic_year}"

                elif 'year' in extracted_values and len(extracted_values) == 1:
                    # Only year format
                    return self.convert_to_indo_arabic_numbers(extracted_values['year'])
                
                else:
                    # Regular date format with day, month, year
                    year = extracted_values.get('year')
                    month = extracted_values.get('month')
                    day = extracted_values.get('day')

                    # Convert day and year to Indo-Arabic numbers
                    indo_arabic_day = self.convert_to_indo_arabic_numbers(day)
                    indo_arabic_year = self.convert_to_indo_arabic_numbers(year)

                    # Remove leading zero from the Indo-Arabic day
                    indo_arabic_day = re.sub(r'^٠', '', indo_arabic_day)

                    # Convert month to Kurdish name
                    month_name = self.convert_month(month)

                    # Return the formatted date in Kurdish
                    return f"{indo_arabic_day}ی {month_name}ی {indo_arabic_year}"

        return date_str

    def fix_date_parameters(self, template_content: str) -> str:
        """Fix date formats for specific parameters only if they match predefined patterns."""
        parameters = ['ڕێکەوت', 'ڕێکەوتی سەردان', 'ڕێکەوتی ئەرشیڤ']
        modified = False  # Track if any modification is made

        for param in parameters:
            def replace_date(match):
                original_value = match.group(2).strip()
                fixed_value = self.fix_date_format(original_value)
                if fixed_value != original_value:
                    nonlocal modified  # Mark that a modification has occurred
                    modified = True
                    return f"{match.group(1)}{fixed_value}"
                return match.group(0)

            template_content = re.sub(
                rf'(\|\s*{param}\s*=\s*)([^|}}]+)',
                replace_date,
                template_content
            )

        if modified:
            template_content = template_content.strip()  # Strip only if changes were made
            self.generate_edit_summary("بەکوردیکردنی شێوازی ڕێکەوتەکان")

        return template_content
    
    def fix_timestamp_mismatch(self, template_content: str) -> str:
        """
        Fix timestamp mismatch for archive date based on archive URL.
        https://en.wikipedia.org/wiki/Help:CS1_errors#archive_date_url_ts_mismatch
        """
        modified = False  # Flag to track if any modification occurs

        # Find all occurrences of |ناونیشانی ئەرشیڤ=
        for match in re.finditer(r'\|\s*ناونیشانی ئەرشیڤ\s*=\s*(https?://[^\s|}]+)', template_content):
            archive_url = match.group(1)

            # Check if the URL contains a 14-digit timestamp and extract the first 8 digits
            timestamp_match = re.search(r'(\d{8})\d{6}', archive_url)
            if timestamp_match:
                timestamp = timestamp_match.group(1)  # Get the first 8 digits (YYYYMMDD)

                # Convert the timestamp to the correct date format
                fixed_date = self.fix_date_format(timestamp)

                # Find the |ڕێکەوتی ئەرشیڤ= parameter and preserve its original spacing
                date_pattern = r'(\|\s*ڕێکەوتی ئەرشیڤ\s*=\s*)([^|}]+)'
                new_template_content = re.sub(
                    date_pattern,
                    # Replace the parameter value only if the stripped current value (m.group(2).strip())
                    # is different from the fixed_date. Otherwise, leave the entire match (m.group(0)) unchanged.
                    lambda m: f"{m.group(1)}{fixed_date}" if m.group(2).strip() != fixed_date else m.group(0),
                    template_content
                )

                # Check if any modification was made
                if new_template_content != template_content:
                    template_content = new_template_content  # Update template content
                    modified = True  # Mark as modified if the content changed

        if modified:
            self.generate_edit_summary("چاکسازیی ڕێکەوتی ئەرشیڤ")
        return template_content
    
    def remove_wikimarkup_from_parameters(self, template_content: str) -> str:
        """
        Remove italic and bold markup from specific parameters' values.
        https://en.wikipedia.org/wiki/Help:CS1_errors#apostrophe_markup
        """
        parameters = [
            # List of parameters to process
            'periodical', 'بڵاوکەرەوە', 'ژوورناڵ', 'گۆڤار', 'ڕۆژنامە', 'وێبگە', 'ئیش', 'بەرھەم'
            ]

        def remove_wikimarkup(value: str) -> str:
            # Remove both bold (''') and italic ('') wikimarkup
            value = re.sub(r"'''(.*?)'''", r"\1", value)  # For bold
            value = re.sub(r"''(.*?)''", r"\1", value)  # For italic
            return value
        
        modified = False  # Track if any modification is made

        for param in parameters:
            # Refined regex to handle internal/external links with pipes and ensure closing quotes match
            pattern = rf'(\|\s*{param}\s*=\s*)(\'\'\'?)(.*?)(\'\'\'?)'
            new_template_content = re.sub(
                pattern,
                lambda m: f"{m.group(1)}{remove_wikimarkup(m.group(3).strip())}",
                template_content
            )

            # Check if any modification was made
            if new_template_content != template_content:
                template_content = new_template_content  # Update template content
                modified = True  # Mark as modified if the content changed

        if modified:
            template_content = template_content.strip()  # Strip only if changes were made
            self.generate_edit_summary("لابردنی ماڕکئەپی ناپێویستی ویکی")

        return template_content
    
    def generate_edit_summary(self, action: str) -> None:
        """Append unique action details to the edit summary."""
        if not hasattr(self, 'edit_summary'):
            self.edit_summary = set()  # Use a set to store unique actions

        if action not in self.edit_summary:
            self.edit_summary.add(action)

    def treat_page(self) -> None:
        """Load the given page, do some changes, and save it."""
        
        self.edit_summary.clear()  # Clear previous summaries before processing a new page

        text = self.current_page.text

        # Process the text for updating template names in specific templates
        for old_template, new_template in self.template_name_mapping.items():
            # Create a regex pattern to match the template with its parameters
            template_pattern = re.compile(r'{{\s*' + re.escape(old_template) + r'\s*(\|[^{}]*(?:{{.*?}}[^{}]*)*)}}', re.IGNORECASE | re.DOTALL)
            # Find all instances of the template in the text
            matches = template_pattern.findall(text)

            # If any matches are found, process the parameters and update the template name
            if matches:
                # Update the template name only if there are parameters to update
                if old_template != new_template: # Prevent substitution if names are identical
                    text = re.sub(r'{{\s*' + re.escape(old_template) + r'\s*\|', '{{' + new_template + '|', text, flags=re.IGNORECASE)

                # Process each instance of a matched template found in the text.
                for match in matches:
                    # Capture the entire template including parameters
                    template_content = match  # Content of the matched template

                    # Update old parameter names with the new one within the matched template
                    template_content = self.update_parameter_names(template_content)
                        
                    # Remove empty parameters if the option is set
                    if self.opt.remove_empty:
                        template_content = self.remove_empty_parameters(template_content)

                    # Convert numbered parameters to Indo-Arabic numbers
                    template_content = self.convert_numbered_parameter_values(template_content)

                    template_content = self.fix_date_parameters(template_content)

                    # Replace invalid values after all parameter names have been updated
                    template_content = self.replace_invalid_values(template_content)

                    # Remove duplicate parameters with the same value before replacing the template content
                    template_content = self.remove_duplicate_parameters(template_content)

                    # Fix the timestamp mismatch between |archive-url= and |archive-date=
                    template_content = self.fix_timestamp_mismatch(template_content)

                    # Remove italic and bold markup from specific parameters' values.
                    template_content = self.remove_wikimarkup_from_parameters(template_content)

                    # Replace the original template content with the updated one
                    text = text.replace(match, template_content)

        # Format the edit summary
        base_summary = "؛ ".join(list(self.edit_summary))
        summary = self.opt.summary or f"بۆت: {base_summary} (بە بەکارھێنانی [[وپ:نپس]])"

        # Save the page with the generated summary
        self.put_current(text, summary=summary)

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
                print('Please enter a value for ' + arg)
            options[option] = value
        else:
            options[option] = True

    # Create a generator for pages
    gen = gen_factory.getCombinedGenerator(preload=True)

    # Create and run the bot
    if not pywikibot.bot.suggest_help(missing_generator=not gen):
        bot = CiteParamUpdaterBot(generator=gen, **options)
        bot.run()  # Runs the bot

if __name__ == '__main__':
    main()
    