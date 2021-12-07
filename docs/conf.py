# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

project = 'JSPR'
copyright = '2021, vector-of-bool'
author = 'vector-of-bool'

# type: ignore

# The full version, including alpha/beta/rc tags
release = '0.1.0'

extensions = []

templates_path = []

html_theme = 'nature'

html_static_path = []

highlight_language = 'jspr'

# html_css_files = ['tweaks.css']

pygments_style = 'friendly'

import copy

from pygments.lexers.data import YamlLexer, bygroups, Name, Punctuation, Text
from pygments.token import Keyword, Literal


class JSPRLexer(YamlLexer):
    name = 'JSPR'
    aliases = ['jspr']

    VARSET_RE = (r'([ ]*)([\w.@-]+)(=(\'|(:.+?))?:)(?=[ ]|$)', bygroups(Text, Name.Variable, Punctuation))
    VARREF_RE = (r'([ ]*)(\.)([\w.@-]+)', bygroups(Text, Punctuation, Name.Variable))
    KEYWORD_RE = (r'([ ]*)(if|then|else|do|quote|lambda|let|assert)((\'|(:.+?))?:)(?=[ ]|$)',
                  bygroups(Text, Keyword, Punctuation))
    KEY_COLON = (r'''([^,:?\[\]{}"'\n][^,:?\[\]{}\n]+)((\'|(:.+?))?:)(?=[ ]|$)''', bygroups(Name.Tag, Punctuation))
    prepend = [
        VARSET_RE,
        VARREF_RE,
        KEYWORD_RE,
        KEY_COLON,
    ]

    tokens = copy.deepcopy(YamlLexer.tokens)
    fseq = tokens['flow-sequence']
    fseq = prepend + fseq
    tokens['flow-sequence'] = fseq

    bline = tokens['block-line']
    bline.insert(2, KEY_COLON)
    bline.insert(2, VARSET_RE)
    bline.insert(2, KEYWORD_RE)

    BOOL_RE = (r'([Tt]rue|[Ff]alse|[Nn]o|[Yy]es)(?![\w-])+', Literal.Number)
    NUMBER_RE = (r'\d+(\.(\d+)?)?', Literal.Number)
    for k in ('flow', 'block'):
        key = f'plain-scalar-in-{k}-context'
        l = tokens[key]
        for rule in (BOOL_RE, NUMBER_RE):
            l.insert(-1, rule)

    # Bare words should be treated as strings
    STRING_RE = (r'(?::(?!\s)|[^\s:\]\}])+', Literal.String)
    tokens['plain-scalar-in-block-context'].insert(-1, STRING_RE)
    # In a flow context (between brackets), a bare comma is not part of a string
    STRING2_RE = (r'(?::(?!\s)|[^\s,:\]\}])+', Literal.String)
    tokens['plain-scalar-in-flow-context'].insert(-1, STRING2_RE)


from sphinx.highlighting import lexers

lexers['jspr'] = JSPRLexer()
