# bootstrap easy_install
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup

setup(
    name = 'solrpy',
    version = '0.1',
    url = 'http://cheeseshop.python.org/pypi/solrpy',
    license = 'http://opensource.org/licenses/apache2.0.php',
    py_modules = ['solr'],
    install_requires = [],
    description = 'client for the solr search service',
    tests_require = ["nose>=0.10.1"],
    test_suite = 'nose.collector',
)
