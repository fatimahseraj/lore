"""
Initialize signals for indexing the search engine. This allows us to
automatically update the index for a LearningResource when it has terms
added to or removed from a vocabulary. The HAYSTACK_SIGNAL_PROCESSOR value
in settings.py handles the save of a LearningResource, but not
many-to-many fields.
"""

import logging

from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
from statsd.defaults.django import statsd

log = logging.getLogger(__name__)


# pylint: disable=unused-argument
@statsd.timer('lore.haystack.taxonomy_update')
@receiver(m2m_changed)
def handle_m2m_save(sender, **kwargs):
    """Update index when taxonomies are updated."""
    from search.search_indexes import get_vocabs
    instance = kwargs.pop("instance")
    if instance.__class__.__name__ != "LearningResource":
        return
    # Update cache for the LearningResource if it's already set.
    get_vocabs(instance.id)
    # Update Elasticsearch index:
    from search.utils import index_resources
    index_resources([instance.id])


@statsd.timer('lore.elasticsearch.taxonomy_update')
@receiver(post_save)
def handle_resource_update(sender, **kwargs):
    """Update index when a LearningResource is updated."""
    if kwargs["created"]:
        # Don't index upon create because we handle this in bulk
        # in the importer, the only place we allow creation to happen.
        return
    instance = kwargs.pop("instance")
    if instance.__class__.__name__ != "LearningResource":
        return
    from search.utils import index_resources
    index_resources([instance.id])


@statsd.timer('lore.elasticsearch.taxonomy_delete')
@receiver(post_delete)
def handle_resource_deletion(sender, **kwargs):
    """Delete index when instance is deleted."""
    # We currently only use this in tests, the user cannot delete resources
    # at the moment.
    instance = kwargs.pop("instance")
    if instance.__class__.__name__ != "LearningResource":
        return
    from search.utils import delete_resource_from_index
    delete_resource_from_index(instance)
