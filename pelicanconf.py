#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Riley Avron'
SITENAME = 'ravron'
SITEURL = ''

PATH = 'content'

DEFAULT_DATE_FORMAT = '%Y-%m-%d'
TIMEZONE = 'America/Los_Angeles'

DEFAULT_LANG = 'en'

THEME = 'themes/pelican-alchemy/alchemy'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Jinja2', 'http://jinja.pocoo.org/'),
         ('You can modify those links in your config file', '#'),)

# TODO: Edit css to roundify this
SITEIMAGE = 'https://www.gravatar.com/avatar/b6dda2f05f2182e4ad1cf20cb6fa9872?s=128'

DESCRIPTION = ''

HIDE_AUTHORS = True

ICONS = (
    ('github', 'https://github.com/ravron'),
    ('stack-overflow', 'https://stackoverflow.com/users/1292061'),
)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
