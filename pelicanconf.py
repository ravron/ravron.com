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
#LINKS = (('Pelican', 'http://getpelican.com/'),
#         ('Python.org', 'http://python.org/'),
#         ('Jinja2', 'http://jinja.pocoo.org/'),
#         ('You can modify those links in your config file', '#'),)
LINKS = ()

# TODO: Edit css to roundify this
SITEIMAGE = '/images/weasel-avatar.png width=150 height=150'

DESCRIPTION = ''

HIDE_AUTHORS = True

ICONS = (
    ('github', 'https://github.com/ravron'),
    ('stack-overflow', 'https://stackoverflow.com/users/1292061'),
)

DEFAULT_PAGINATION = 10

STATIC_PATHS = ['extras', 'images']
EXTRA_PATH_METADATA = {
        'extras/android-chrome-192x192.png': {'path': 'android-chrome-192x192.png'},
        'extras/android-chrome-512x512.png': {'path': 'android-chrome-512x512.png'},
        'extras/apple-touch-icon.png': {'path': 'apple-touch-icon.png'},
        'extras/browserconfig.xml': {'path': 'browserconfig.xml'},
        'extras/favicon-16x16.png': {'path': 'favicon-16x16.png'},
        'extras/favicon-32x32.png': {'path': 'favicon-32x32.png'},
        'extras/favicon.ico': {'path': 'favicon.ico'},
        'extras/manifest.json': {'path': 'manifest.json'},
        'extras/mstile-150x150.png': {'path': 'mstile-150x150.png'},
        'extras/safari-pinned-tab.svg': {'path': 'safari-pinned-tab.svg'},
}

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
