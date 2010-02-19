# bootstrap easy_install
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = 'solrpy',
    version = '1.0', # don't forget to update solr.core.__version__
    url = 'http://code.google.com/p/solrpy',
    license = 'http://opensource.org/licenses/apache2.0.php',
    packages=find_packages(),
    install_requires = [],
    description = 'client for the solr search service',
    tests_require = ["nose>=0.10.1"],
    test_suite = 'nose.collector',
)
