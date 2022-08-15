# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'Account Abstraction'
copyright = '2022, Infinitism'
author = 'Dror Tirosh'

release = '0.1'
version = '0.1.0'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.extlinks'
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

extlinks = {
    'eip-2938': ('https://eips.ethereum.org/EIPS/eip-2938', ''),
    'eth1.x': ('https://ethereum-magicians.org/t/implementing-account-abstraction-as-part-of-eth1-x/4020', ''),
    'eip-4337': ('https://eips.ethereum.org/EIPS/eip-4337', '')
}

intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'
