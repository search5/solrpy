# bootstrap easy_install
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name = 'solrpy',
    version = '0.6',
    url = 'http://code.google.com/p/solrpy',
    license = 'http://opensource.org/licenses/apache2.0.php',
    packages=find_packages(exclude=['ez_setup']),
    install_requires = [],
    description = 'client for the solr search service',
    tests_require = ["nose>=0.10.1"],
    test_suite = 'nose.collector',
)
