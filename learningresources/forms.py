"""
Forms for LearningResources
"""

from __future__ import unicode_literals

from django.forms import ModelForm
from django.utils.text import slugify
from django.db import transaction

from .models import Course, Repository

# pylint: disable=missing-docstring


class CourseForm(ModelForm):
    """
    Form for the Course object.
    """
    class Meta:
        model = Course
        fields = (
            "repository", "org", "course_number", "run", "imported_by"
        )


class RepositoryForm(ModelForm):
    """
    Form for the Course object.
    """
    class Meta:
        model = Repository
        fields = ("name", "description")

    # pylint: disable=signature-differs
    # The ModelForm.save() accepts "commit" and this doesn't, because
    # we always set commit=False then add the user because created_by is
    # not part of the form, and shouldn't be.
    @transaction.atomic
    def save(self, user):
        """
        Save a newly-created form.
        """
        repo = super(RepositoryForm, self).save(commit=False)
        slug = slugify(repo.name)
        count = 1
        while Repository.objects.filter(slug=slug).exists():
            slug = "{0}{1}".format(slugify(repo.name), count)
            count += 1
        repo.slug = slug
        repo.created_by = user
        repo.save()
        return repo
