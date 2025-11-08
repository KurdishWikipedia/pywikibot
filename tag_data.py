# -*- coding: utf-8 -*-

"""
This file serves as the central configuration hub for the tag bot.

It contains all data and settings that control the bot's behavior, separating
configuration from the operational logic in the main script.

Note:
For the bot to function fully on your wiki, please ensure local templates exist for:
- {{Multiple issues}} (Q6450720)
- {{DATE}} for date substitution (Q7747897)
-  Supported tags defined in `default` section that the bot can add/remove.
"""

# Defines the behavior for tags the bot can ADD or REMOVE.
#
# --- Language-Specific Overrides ---
# To customize behavior for your wiki, add your language code (e.g., 'fr')
# and specify ONLY the properties you want to change for a specific tag.
#
# Overridable Properties:
#   - "addable": (bool) Can the bot add this tag?
#   - "removable": (bool) Can the bot remove this tag?
#   - "params": (str)  Wikitext for parameters (e.g., "|date=...").
#
TAG_DEFINITIONS = {
    # WARNING: Please do not edit the 'default' section unless you know what you are doing.
    'default': {
        "unreferenced":     {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
        "one_source":       {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
        "blp_unreferenced": {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
        "blp_one_source":   {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
        "deadend":          {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
        "orphan":           {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
        "uncategorized":    {"addable": True, "removable": True, "params": "|{{subst:DATE}}"},
    },

    # Language-specific overrides start here.
    # 'fr': {
    #     "unreferenced": {"removable": False}, # Example: Disable removing the 'unreferenced' tag on fr.wiki.
    # },
}

# Language-specific messages for generating edit summaries.
# Falls back to 'en' if the site language is not defined here.
SUMMARY_MESSAGES = {
    'en': {
        'bot_prefix': 'Bot: ',
        'adding': 'Adding',
        'removing': 'Removing',
        'tag': 'tag',
        'tags': 'tags',
        'and': ' and ',
        'comma_separator': ', ',
        'separator': '; ',
        'template_ns': 'Template',
    },
    'ckb': {
        'bot_prefix': 'بۆت: ',
        'adding': 'زیادکردنی',
        'removing': 'لابردنی',
        'tag': 'تاگی',
        'tags': 'تاگەکانی',
        'and': ' و ',
        'comma_separator': '، ',
        'separator': '؛ ',
        'template_ns': 'داڕێژە',
    },
}

MULTIPLE_ISSUES_QID = 'Q6450720' # Template:Multiple issues

# Used to identify BLP articles.
LIVING_PEOPLE_CATEGORY_QID = 'Q5312304'  # Category:Living people

# QIDs for common citation templates, used to detect references without <ref> tags.
CITATION_TEMPLATES_QIDS = [
    'Q6925554',  # citation
    'Q92570',    # cite book
    'Q5624899',  # cite journal
    'Q5625676',  # cite news
    'Q5637226',  # cite web
]

# Defines the layout order of templates that appear above maintenance tags.
LAYOUT_TEMPLATES_BY_PRIORITY = [
    # Before hatnotes
    'Q52083446', # Template:short description
    'Q7748394', # Template:DISPLAYTITLE
    'Q4282320', # Template:Lowercase title
    'Q5805831', # Template:Italic title
    # Hatnotes
    'Q5625128', # Template:hatnote
    'Q6797933', # Template:main
    'Q6383276', # Template:correct title
    'Q118038211', # Template:distinguish
    'Q6176023', # Template:for
    'Q6215759', # Template:further
    'Q5622390', # Template:Self-reference
    'Q14452336', # Template:about year
    'Q20750675', # Template:similar names
    'Q22742328', # Template:highway detail hatnote
    'Q19676997', # Template:broader
    'Q6667048', # Template:about-distinguish
    'Q25990535', # Template:about other people
    'Q5766677', # Template:about
    'Q22756090', # Template:other storms
    'Q6501382', # Template:other people
    'Q13360194', # Template:other places
    'Q13108237', # Template:other ships
    'Q5758947', # Template:other uses
    'Q13099245', # Template:other uses of
    'Q6042392', # Template:redirect
    'Q14449133', # Template:redirect-distinguish
    'Q13421042', # Template:redirect-synonym
    'Q25977434', # Template:redirect-multi
    'Q13667217', # Template:see Wiktionary
    'Q5538331', # Template:see also
    'Q62073361', # Template:see also if exists
    # Featured badges
    'Q5857568', # Template:Featured list
    'Q5626124', # Template:Featured article
    'Q5303', # Template:Good article
    # Speedy deletion tags
    'Q6535594', # Template:Db-g1
    'Q10954700', # Template:Db-g2
    'Q10988846', # Template:Db-g3
    'Q7479432', # Template:Db-hoax
    'Q11453769', # Template:Db-g4
    'Q11454960', # Template:Db-g5
    'Q11455750', # Template:Db-g6
    'Q13218936', # Template:Db-copypaste
    'Q25971427', # Template:Db-error
    'Q13218917', # Template:Db-move
    'Q106312912', # Template:Db-moved
    'Q13107189', # Template:Db-xfd
    'Q110936998', # Template:Db-afc-move
    'Q9634684', # Template:Db-g7
    'Q11457965', # Template:Db-g8
    'Q11459573', # Template:Db-g10
    'Q13218913', # Template:Db-negublp
    'Q11460470', # Template:Db-g11
    'Q10989772', # Template:Db-g12
    'Q10989772', # Template:Db-g12
    'Q13218935', # Template:Db-g14
    'Q12470007', # Template:Db-a1
    'Q12470008', # Template:Db-a2
    'Q13218934', # Template:Db-empty
    'Q12470022', # Template:Db-a7
    'Q6806662', # Template:Db-person
    'Q13218938', # Template:Db-band
    'Q13218937', # Template:Db-club
    'Q6806656', # Template:Db-inc
    'Q6806673', # Template:Db-web
    'Q13218939', # Template:Db-animal
    'Q15622820', # Template:Db-event
    'Q12470024', # Template:Db-a9
    'Q12470026', # Template:Db-a10
    'Q16605081', # Template:Db-a11
    # # Proposed for deletion
    'Q12857463', # Template:Proposed deletion
    'Q14397354', # Template:Prod blp
    'Q14397353', # Template:Proposed deletion endorsed
    'Q14441550', # Template:Prod-nn
    # Protection
    'Q6466220', # Template:Pp
    'Q7482910', # Template:Pp-move
    'Q14627998', # Template:Pp-pc
    'Q14441548', # Template:Pp-blp
    'Q9037125', # Template:Pp-dispute
    'Q14441546', # Template:Pp-move-dispute
    'Q25976532', # Template:Pp-extended
    'Q9039502', # Template:Pp-semi-indef
    'Q7482910', # Template:Pp-move
    'Q9039353', # Template:Pp-sock
    'Q6704722', # Template:Pp-vandalism
    'Q13566056', # Template:Pp-move-vandalism

    # We have reached the last template!
    'Q6450720', # Template:Multiple issues
    # All other templates such as infoboxes and unsupported templates go under Multiple issues or TAG_DEFINITIONS
    # Please do not add any other templates below. Add them above instead.
]


# Master dictionary of all known maintenance and cleanup tags, defining their QID and global sort order.
#
# IMPORTANT: The order of keys in this dictionary is the single source of truth for
# the sorting priority inside {{Multiple issues}} across all wikis.
#
# The priority is based on tag type, with Content issues (e.g., unreferenced, POV)
# placed before Style issues (e.g., deadend, orphan, cleanup).
ALL_TAGS_BY_PRIORITY = {
    # --- Red: Special/rare cases ---
    "undisclosed_paid": "Q28522885",

    # --- Orange: Content Issues (Highest Priority) ---
    "unreferenced": "Q5962027", # SUPPORTED TAG
    "one_source": "Q5620159", # SUPPORTED TAG
    "blp_unreferenced": "Q6708313", # SUPPORTED TAG
    "blp_one_source": "Q81934336", # SUPPORTED TAG
    "more_citations_needed": "Q5619503",
    "blp_sources": "Q6708297",
    "notability": "Q6459976",
    "update": "Q5617874",
    "primary_sources": "Q13365792",
    "promotional": "Q6583806",
    "original_research": "Q6526878",
    "coi": "Q6737821",
    "lead_too_short": "Q5618428",
    "independent_sources": "Q13534686",
    "unreliable_sources": "Q7780349",
    "cleanup_rewrite": "Q6473982",
    "globalize": "Q5877521",
    "missing_information": "Q10953923",
    "pov": "Q6294435",
    "self-published": "Q14455639",
    "cleanup_press_release": "Q14337818",
    "disputed": "Q5618260",
    "autobiography": "Q6705258",
    "fan_pov": "Q5621019",
    "expert_needed": "Q6929750",
    "in-universe": "Q6623577",
    "peacock": "Q8644341",
    "how-to": "Q13411298",
    "weasel": "Q7780480",
    "unfocused": "Q14473791",
    "undue_weight": "Q18145477",
    "paid_contributions": "Q25970985",
    "too_few_opinions": "Q18145476",
    "lead_missing": "Q11169781",
    "contradicts_others": "Q7648384",
    "npov_language": "Q24237762",
    "fiction": "Q13421307",
    "close_paraphrasing": "Q7641121",

    # --- Yellow: Style Issues (Lower Priority) ---
    "deadend": "Q5621858", # SUPPORTED TAG
    "orphan": "Q5754827", # SUPPORTED TAG
    "uncategorized": "Q5884621", # SUPPORTED TAG (handled separately for bottom placement.)
    "more_footnotes_needed": "Q5622270",
    "no_footnotes": "Q6867401",
    "no_plot": "Q14399120",
    "cleanup": "Q5624688",
    "tone": "Q5858353",
    "essay-like": "Q7211526",
    "citation_style": "Q5618775",
    "resume-like": "Q7481565",
    "long_plot": "Q10971078",
    "overly_detailed": "Q13518229",
    "more_plot": "Q14398290",
    "prose": "Q5616140",
    "technical": "Q6839519",
    "cleanup_bare_urls": "Q6746581",
    "external_links": "Q13365838",
    "context": "Q7648212",
    "confusing": "Q7646707",
    "cleanup_reorganize": "Q13433594",
    "all_plot": "Q6676442",
    "copy_edit": "Q6292692",
    "convert_to_episode_table": "Q135849488",
    "lead_rewrite": "Q5616697",
    "lead_too_long": "Q10988907",
    "very_long": "Q5618853",
    "cleanup_lang": "Q7639966",
    "excessive_examples": "Q14473738",
    "cleanup_section": "Q7640087",
    "cleanup_mos": "Q14473826",
    "in_popular_culture": "Q14473789",
    "travel_guide": "Q14450719",
    "recentism": "Q5896905",
    "cleanup_biography": "Q7639925",
    "too_many_sections": "Q7646501",
    "story": "Q14455745",
    "buzzword": "Q6734300",
    "dictionary_definition": "Q15599246",
    "unsorted_list": "Q6676752",
    "duplication": "Q14399173",
    "review": "Q13421187",
    "too_many_photos": "Q14398993",
    "cleanup_school": "Q7639994",
    "directory": "Q19753394",
    "underlinked": "Q13107723",
}