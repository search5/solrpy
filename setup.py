# bootstrap easy_install
import sys

try:
    import ez_setup
    ez_setup.use_setuptools()
except:
    pass

from setuptools import setup, find_packages

__version__ = '0.9.9'

setup(
    name='solrpy',
    # We can do this because we don't rely on getting "built" to be importable:
    version=__version__, # update only solr.core.__version__
    url='http://code.google.com/p/solrpy',
    license='http://opensource.org/licenses/apache2.0.php',
    packages=find_packages(),
    install_requires=["future", "six"],
    description='Client for the Solr search service',
    tests_require=["future", "six", "nose>=0.10.1"],
    test_suite='nose.collector'
)
