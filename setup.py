# bootstrap easy_install
from setuptools import setup, find_packages
import sys

#support for python2 and python3
if sys.version_info[0] == 2:
    base_dir = 'python2'
elif sys.version_info[0] == 3:
    base_dir = 'python3'

setup(
    name = 'solrpy3',
    version = '0.98',
    author = 'Ed Summers',
    author_email = 'ehs@pobox.com',
    url = 'https://github.com/edsu/solrpy',
    license = 'http://opensource.org/licenses/apache2.0.php',
    packages=['solr'],
    package_dir={
        'solr' : base_dir + '/solr',
    },
    description = 'Client for the Solr search service',
    tests_require = ["nose>=0.10.1"],
    test_suite = 'nose.collector',

    classifiers=
    [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python'
    ],

)
