# bootstrap easy_install
import sys

if sys.version_info[0] == 2:
    import ez_setup
    ez_setup.use_setuptools()

from setuptools import setup, find_packages
import solr.core

setup(
    name = 'solrpy',
    # We can do this because we don't rely on getting "built" to be importable:
    version = solr.core.__version__, # update only solr.core.__version__
    url = 'http://code.google.com/p/solrpy',
    license = 'http://opensource.org/licenses/apache2.0.php',
    packages=find_packages(),
    install_requires = ["future", "six"],
    description = 'Client for the Solr search service',
    tests_require = ["future", "six", "nose>=0.10.1"],
    test_suite = 'nose.collector',
    )
