#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('./'))

from run_test import setup_django_environment

setup_django_environment()

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'alabaster',
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = 'django-pg-timepart'
copyright = '2019, Chaitin Tech'
author = 'Boyce Li'

language = 'en'

exclude_patterns = ['_build']

pygments_style = 'sphinx'

html_theme = 'alabaster'

html_theme_options = {
    'logo': 'img/logo.gif',
    'github_user': 'chaitin',
    'github_repo': 'django-pg-timepart',
    'github_type': 'star',
    'github_banner': 'true',
    'show_powered_by': 'false',
    'code_font_size': '14px',
}

html_static_path = ['_static']

html_sidebars = {
    '**': [
        'sidebarlogo.html',
        'navigation.html',
        'searchbox.html',
    ]
}

htmlhelp_basename = 'django-pg-timepart-doc'

man_pages = [
    (master_doc, 'django-pg-timepart', 'django-pg-timepart Documentation',
     [author], 1)
]

texinfo_documents = [
    (master_doc, 'django-pg-timepart', 'django-pg-timepart Documentation',
     author, 'django-pg-timepart', 'A Django extension that provides database table partition management.',
     'Miscellaneous'),
]

intersphinx_mapping = {
    'https://docs.python.org/3/': None,
    'https://pika.readthedocs.io/en/0.10.0/': None,
}

add_module_names = False
