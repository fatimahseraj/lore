"""
Functions for search functionality.
"""

from __future__ import unicode_literals

from search.sorting import LoreSortingFields
from search.utils import search_index
from taxonomy.models import Vocabulary, Term


def construct_queryset(repo_slug, query='', selected_facets=None, sortby=''):
    """
    Create a SearchQuerySet given search parameters.

    Args:
        repo_slug (learningresources.models.Repository):
            Slug for repository being searched.
        query (unicode): If present, search phrase to use in queryset.
        selected_facets (list or None):
            If present, a list of facets to narrow the search with.
        sortby (unicode): If present, order by this sorting option.
    Returns:
        search.utils/SearchResults: The search results.
    """

    if selected_facets is None:
        selected_facets = []

    kwargs = {}
    if query != "":
        kwargs["content"] = query

    if sortby == "":
        sortby = LoreSortingFields.DEFAULT_SORTING_FIELD
    # default values in case of weird sorting options
    sortby, _, order_direction = LoreSortingFields.get_sorting_option(
        sortby)
    sortby = "{0}{1}".format(order_direction, sortby)

    # Do a parallel query using elasticsearch-dsl.
    if query not in ("", None):
        tokens = query
    else:
        tokens = None
    terms = {}
    for facet in selected_facets:
        key, value = facet.split(":")

        # Haystack queries for blanks by putting the key last, as the value,
        # and setting the key to "_missing_." Fix  this for elasticsearch-dsl.
        if key == '_missing_':
            key, value = value, "empty"

        if key.endswith("_exact"):
            key = key[:-6]

        # Look for facets
        if key.isdigit():
            key = get_vocab_name(key)
            if value is not 'empty':
                value = get_term_label(value)
        terms[key] = value

    # This is sneakily being returned instead of the
    # Haystack queryset created above.
    results = search_index(
        tokens=tokens,
        repo_slug=repo_slug,
        sort_by=sortby,
        terms=terms,
    )

    return results


def get_vocab_name(vocab_id):
    """Get vocabulary name by ID."""
    vocab = Vocabulary.objects.get(id=vocab_id)
    return vocab.name


def get_term_label(term_id):
    """Get term label by ID."""
    return Term.objects.get(id=term_id).label
