Open511 aims to make roadwork data open and shareable. Read more at http://blog.opennorth.ca/opening-new-roads-with-open511

This is early prototype code. You probably shouldn't use it.

### Admin notes

For the moment, this package hacks the Django admin just until it works. We don't intend to stick with this in a release version. The current hack is particular about a few things:

* You need to restrict settings.LANGUAGES to the languages you want to support
* 'open511' needs to be higher up in settings.INSTALLED_APPS than django.contrib.admin and django.contrib.gis
* In django.contrib.admin.widgets, lines 35 & 36 (if value.geom_type != self.geom_type) need to be commented out