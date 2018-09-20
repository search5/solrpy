import sys

if sys.version_info[0] == 3:
    from solr.core import *
    from solr.paginator import *
else:
    from core import *
    from paginator import *
