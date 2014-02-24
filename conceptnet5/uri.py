# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
"""
URIs are Unicode strings that represent the canonical name for any object in
ConceptNet. These can be used with the ConceptNet Web API, or referred to in a
Semantic Web application, by attaching the prefix:

    http://conceptnet5.media.mit.edu/data/VERSION

For example, the English concept "book" has the URI '/c/en/book'. This concept
can be referred to, or retrieved, using this complete URI (in version 5.2):

    http://conceptnet5.media.mit.edu/data/5.2/c/en/book
"""

import sys
from ftfy import fix_text


if sys.version_info.major >= 3:
    unicode = str


def normalize_text(text):
    """
    When a piece of a URI is an arbitrary string, we standardize it in the
    following ways:

    - Ensure it is in Unicode, and standardize its Unicode representation
      with the `ftfy.fix_text` function.
    - Erase case distinctions by converting cased characters to lowercase.
    - Strip surrounding whitespace.
    - Replace spaces with underscores.

    The result will be a Unicode string that can be used within a URI.

        >>> normalize_text(' cat')
        'cat'

        >>> normalize_text('Italian supercat')
        'italian_supercat'

        >>> normalize_text('   u\N{COMBINING DIAERESIS}ber\\n')
        'über'
    """
    if not isinstance(text, unicode):
        raise ValueError("All texts must be Unicode, not bytes.")
    text = fix_text(text).strip().lower().replace(' ', '_')
    return text


def join_uri(*pieces):
    """
    `join_uri` builds a URI from constituent pieces that should be joined
    with slashes (/).

    Leading and trailing on the pieces are acceptable, but will be ignored.
    The resulting URI will always begin with a slash and have its pieces
    separated by a single slash.

    The pieces do not have `normalize_text` applied to it; to make sure your
    URIs are in normal form, run `normalize_text` on each piece that represents
    arbitrary text.

        >>> join_uri('/c', 'en', 'cat')
        '/c/en/cat'

        >>> join_uri('c', 'en', ' spaces ')
        '/c/en/ spaces '

        >>> join_uri('/r/', 'AtLocation/')
        '/r/AtLocation'

        >>> join_uri('/test')
        '/test'

        >>> join_uri('test')
        '/test'
        
        >>> join_uri('/test', '/more/')
        '/test/more'

    """
    joined = '/' + ('/'.join([piece.strip('/') for piece in pieces]))
    return joined


def concept_uri(lang, text, pos=None, disambiguation=None):
    """
    `concept_uri` builds a representation of a concept, which is a word or
    phrase of a particular language, which can participate in relations with
    other concepts, and may be linked to concepts in other languages.
    
    Every concept has an ISO language code and a text. It may also have a part
    of speech (pos), which is typically a single letter. If it does, it may
    have a disambiguation, a string that distinguishes it from other concepts
    with the same text.

        >>> concept_uri('en', 'cat')
        '/c/en/cat'
        >>> concept_uri('en', 'cat', 'n')
        '/c/en/cat/n'
        >>> concept_uri('en', 'cat', 'n', 'feline')
        '/c/en/cat/n/feline'
    """
    n_text = normalize_text(text)
    if pos is None:
        if disambiguation is not None:
            raise ValueError("Disambiguated concepts must have a part of speech")
        return join_uri('/c', lang, n_text)
    else:
        if disambiguation is None:
            return join_uri('/c', lang, n_text, pos)
        else:
            n_disambig = normalize_text(disambiguation)
            return join_uri('/c', lang, n_text, pos, n_disambig)


def compound_uri(op, args):
    """
    Some URIs represent a compound structure or operator built out of a number
    of arguments. Some examples are the '/and' and '/or' operators, which
    represent a conjunction or disjunction over two or more URIs, which may
    themselves be compound URIs; or the assertion structure, '/a', which takes
    a relation and two URIs as its arguments.

    This function takes the main 'operator', with the slash included, and an
    arbitrary number of arguments, and produces the URI that represents the
    entire compound structure.

    These structures contain square brackets as segments, which look like
    `/[/` and `/]/`, so that compound URIs can contain other compound URIs
    without ambiguity.

        >>> compound_uri('/nothing', [])
        '/nothing/[/]'
        >>> compound_uri('/a', ['/r/CapableOf', '/c/en/cat', '/c/en/sleep'])
        '/a/[/r/CapableOf/,/c/en/cat/,/c/en/sleep/]'
    """
    items = [op]
    first_item = True
    items.append('[')
    for arg in args:
        if first_item:
            first_item = False
        else:
            items.append(',')
        items.append(arg)
    items.append(']')
    return join_uri(*items)


def parse_compound_uri(uri):
    """
    Given a compound URI, extract its operator and its list of arguments.

        >>> parse_compound_uri('/nothing/[/]')
        ('/nothing', [])
        >>> parse_compound_uri('/a/[/r/CapableOf/,/c/en/cat/,/c/en/sleep/]')
        ('/a', ['/r/CapableOf', '/c/en/cat', '/c/en/sleep'])
    """
    pieces = uri.lstrip('/').split('/')
    if pieces[-1] != ']':
        raise ValueError("Compound URIs must end with /]")
    if '[' not in pieces:
        raise ValueError("Compound URIs must contain /[/ at the beginning of "
                         "the argument list")
    list_start = pieces.index('[')
    op = join_uri(*pieces[:list_start])

    chunks = []
    current = []
    depth = 0
    for piece in pieces[(list_start + 1):-1]:
        if piece == ',' and depth == 0:
            chunks.append('/' + ('/'.join(current)).strip('/'))
            current = []
        else:
            current.append(piece)
            if piece == '[':
                depth += 1
            elif piece == ']':
                depth -= 1
    if current:
        chunks.append('/' + ('/'.join(current)).strip('/'))
    return op, chunks


def conjunction_uri(*sources):
    """
    Make a URI representing a conjunction of sources that work together to provide
    an assertion.

        >>> conjunction_uri('/s/contributor/omcs/dev')
        '/s/contributor/omcs/dev'
        
        >>> conjunction_uri('/s/contributor/omcs/dev', '/rule/some_kind_of_parser')
        '/and/[/s/contributor/omcs/dev/,/rule/some_kind_of_parser/]'
    """
    if len(sources) == 0:
        # Logically, a conjunction with 0 inputs represents 'True', a
        # proposition that cannot be denied. This could be useful for
        # discussing, say, mathematical axioms, but when it comes to
        # ConceptNet, that kind of thing makes us uncomfortable and
        # shouldn't appear in the data.
        raise ValueError("Conjunctions of 0 things are not allowed")
    elif len(sources) == 1:
        return sources[0]
    else:
        return compound_uri('/and', sources)


def disjunction_uri(*sources):
    """
    Make a URI representing a choice of sources that provide the same assertion.

        >>> disjunction_uri('/s/contributor/omcs/dev')
        '/s/contributor/omcs/dev'

        >>> disjunction_uri('/s/contributor/omcs/dev', '/s/contributor/omcs/rspeer')
        '/or/[/s/contributor/omcs/dev/,/s/contributor/omcs/rspeer/]'
    """
    if len(sources) == 0:
        raise ValueError("Disjunctions of 0 things are not allowed")
    elif len(sources) == 1:
        return sources[0]
    else:
        return compound_uri('/or', sources)


def assertion_uri(rel, *args):
    """
    Make a URI for an assertion.

    There will usually be two items in *args, the 'start' and 'end' of the
    assertion. However, this can support relations with different number
    of arguments.

        >>> assertion_uri('/r/CapableOf', '/c/en/cat', '/c/en/sleep')
        '/a/[/r/CapableOf/,/c/en/cat/,/c/en/sleep/]'
    """


def and_or_tree(list_of_lists):
    """
    An and-or tree represents a disjunction of conjunctions. In ConceptNet terms,
    it represents all the reasons we might believe a particular assertion.
    """
    ands = [conjunction_uri(sublist) for sublist in list_of_lists]
    return disjunction_uri(ands)


class License(object):
    cc_attribution = '/l/CC/By'
    cc_sharealike = '/l/CC/By-SA'
