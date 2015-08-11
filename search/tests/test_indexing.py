"""Tests for search engine indexing."""
from __future__ import unicode_literals

import logging

from search.search_indexes import get_course_metadata, get_vocabs, cache
from search.sorting import LoreSortingFields
from search.tests.base import SearchTestCase

log = logging.getLogger(__name__)


def set_cache_timeout(seconds):
    """Override the cache timeout for testing."""
    cache.default_timeout = seconds
    cache.clear()


class TestIndexing(SearchTestCase):
    """Test Elasticsearch indexing."""

    def setUp(self):
        """Remember old caching settings."""
        super(TestIndexing, self).setUp()
        self.original_timeout = cache.default_timeout

    def tearDown(self):
        """Restore old caching settings."""
        super(TestIndexing, self).tearDown()
        cache.default_timeout = self.original_timeout

    def test_index_on_save(self):
        """Index a LearningObject upon creation."""
        search_text = "The quick brown fox."
        self.assertTrue(self.count_results(search_text) == 0)
        self.resource.content_xml = search_text
        self.resource.save()
        self.assertTrue(self.count_results(search_text) == 1)

    def test_index_vocabulary(self):
        """
        Test that LearningResource indexes are updated when a
        a term is added or removed.
        """
        set_cache_timeout(0)
        term = self.terms[0]
        self.assertEqual(self.count_faceted_results(
            self.vocabulary.id, term.id), 0)
        self.resource.terms.add(term)
        self.assertEqual(self.count_faceted_results(
            self.vocabulary.id, term.id), 1)
        self.resource.terms.remove(term)
        self.assertEqual(self.count_faceted_results(
            self.vocabulary.id, term.id), 0)

    def test_strip_xml(self):
        """Indexed content_xml should have XML stripped."""
        xml = "<tag>you're it</tag>"
        self.resource.content_xml = xml
        self.resource.save()
        self.assertTrue(self.count_results("you're it") == 1)
        self.assertTrue(self.count_results(xml) == 0)

    def test_sorting(self):
        """Test sorting for search"""
        # remove the default resource to control the environment
        self.resource.delete()
        # create some resources
        res1 = self.create_resource(**dict(
            resource_type="example",
            title="silly example 1",
            content_xml="<blah>blah 1</blah>",
            mpath="/blah1",
            xa_nr_views=1001,
            xa_nr_attempts=99,
            xa_avg_grade=9.9
        ))
        res2 = self.create_resource(**dict(
            resource_type="example",
            title="silly example 2",
            content_xml="<blah>blah 2</blah>",
            mpath="/blah2",
            xa_nr_views=1003,
            xa_nr_attempts=98,
            xa_avg_grade=6.8
        ))
        res3 = self.create_resource(**dict(
            resource_type="example",
            title="silly example 3",
            content_xml="<blah>blah 3</blah>",
            mpath="/blah3",
            xa_nr_views=1002,
            xa_nr_attempts=101,
            xa_avg_grade=7.3
        ))
        self.assertEqual(self.count_results(''), 3)
        # sorting by number of views
        results = self.search(
            '',
            sorting=LoreSortingFields.SORT_BY_NR_VIEWS[0]
        )
        # expected position (res2, res3, res1)
        top_res = results[0]
        self.assertEqual(
            top_res.nr_views,
            res2.xa_nr_views
        )
        # sorting by number of attempts
        results = self.search(
            '',
            sorting=LoreSortingFields.SORT_BY_NR_ATTEMPTS[0]
        )
        # expected position (res3, res1, res2)
        top_res = results[0]
        self.assertEqual(
            top_res.nr_attempts,
            res3.xa_nr_attempts
        )
        # sorting by average grade
        results = self.search(
            '',
            sorting=LoreSortingFields.SORT_BY_AVG_GRADE[0]
        )
        # expected position (res1, res3, res2)
        top_res = results[0]
        self.assertEqual(
            top_res.avg_grade,
            res1.xa_avg_grade
        )

    def test_indexing_cache(self):
        """
        Test caching -- enabled and disabled.
        This test both the course and taxonomy caches
        from within search/search_indexes.py, because
        both are "faceted" searches.
        """
        def get_count():
            """
            Get the count of a search after changing
            the course_number. This will return different
            results depending on whether caching is enabled.
            """
            # This save() is required to make the caching
            # happen if it's enabled, or delete it if it's disabled.
            # Either way, a clean slate for this test.
            self.resource.save()

            # Remember original value, and prove a resource is found.
            orig = self.course.course_number
            self.assertEqual(self.count_faceted_results("course", orig), 1)

            # Change the course number and make sure indexing
            # is called by saving the resource again.
            self.course.course_number = orig + "blah blah blah"
            self.course.save()
            self.resource.save()

            # Get the result and reset everything.
            count = self.count_faceted_results("course", orig)
            self.course.course_number = orig
            self.course.save()
            self.resource.save()
            return count

        set_cache_timeout(0)
        with self.assertNumQueries(23):
            self.assertEqual(get_count(), 0)

        set_cache_timeout(60)
        with self.assertNumQueries(8):
            self.assertEqual(get_count(), 1)

    def test_course_cache(self):
        """
        Test caching -- enabled and disabled -- for course metadata.
        """
        def three_times():
            """Get course metadata three times."""
            for _ in range(0, 3):
                get_course_metadata(self.course.id)

        set_cache_timeout(0)
        with self.assertNumQueries(3):
            three_times()

        set_cache_timeout(60)
        with self.assertNumQueries(1):
            three_times()

    def thrice(self):
        """Hit vocabs three times with and without caching."""
        def three_times():
            """Get vocab data three times."""
            for _ in range(0, 3):
                get_vocabs(self.course.id, self.resource.id)

        set_cache_timeout(0)
        with self.assertNumQueries(6):
            three_times()

        set_cache_timeout(60)
        with self.assertNumQueries(2):
            three_times()

    def test_term_cache_with_data(self):
        """
        Test caching -- enabled and disabled -- for vocabularies.
        This should work if there are vocabulary terms, because
        there is something to cache.
        """
        self.resource.terms.add(self.terms[0])
        self.thrice()

    def test_term_cache_without_data(self):
        """
        Test caching -- enabled and disabled -- for vocabularies.

        This should work if there are not vocabulary terms.
        Otherwise, it'll reload the cache for an entire course whenever
        a LearningResource isn't tagged with any terms.
        """
        self.thrice()
