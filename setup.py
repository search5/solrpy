# bootstrap easy_install
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = 'solrpy',
    version = '0.9.2', # don't forget to update solr.core.__version__
    url = 'http://code.google.com/p/solrpy',
    license = 'http://opensource.org/licenses/apache2.0.php',
    packages=find_packages(),
    install_requires = [],
    description = 'Client for the Solr search service',
    long_description=open('README.txt').read(),
    tests_require = ["nose>=0.10.1"],
    test_suite = 'nose.collector',
    )
