# bootstrap easy_install
from setuptools import setup, find_packages

try:
    import ez_setup
    ez_setup.use_setuptools()
except:
    pass

with open('README.md') as f:
    long_description = f.read()

__version__ = '0.9.9'

setup(
    name='solrpy',
    # We can do this because we don't rely on getting "built" to be importable:
    version=__version__, # update only solr.core.__version__
    url='http://code.google.com/p/solrpy',
    license='http://opensource.org/licenses/apache2.0.php',
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type='text/markdown',  # This is important!
    install_requires=["future", "six", "pyyaml"],
    description='Client for the Solr search service',
    tests_require=["future", "six", "nose>=0.10.1"],
    test_suite='nose.collector'
)
