import re

with open("tests/test_ebay_taxonomy.py", "r") as f:
    content = f.read()

content = content.replace("from laptopfinder.runners import ebay_hunter", "from laptopfinder.runners.hunter import api, search")
content = content.replace('patch("laptopfinder.runners.ebay_hunter.ebay_get"', 'patch("laptopfinder.runners.hunter.api.ebay_get"')
content = content.replace("ebay_hunter.browse_search", "api.browse_search")
content = content.replace("ebay_hunter.collect_corpus", "search.collect_corpus")
content = content.replace("ebay_hunter._build_filter", "search._build_filter")

with open("tests/test_ebay_taxonomy.py", "w") as f:
    f.write(content)
