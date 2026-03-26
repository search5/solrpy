import os
import sys

sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

project = 'solrpy'
copyright = '2010-2026, solrpy developers'
author = 'solrpy developers'

version = '1.0.2'
release = '1.0.2'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = ['_build']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_show_sourcelink = False
html_domain_indices = False

htmlhelp_basename = 'solrpydoc'

# -- Intersphinx mapping -----------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# -- Autodoc options ---------------------------------------------------------

autodoc_member_order = 'bysource'
