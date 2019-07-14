+++
title = "Querying the unicode database"
date = 2019-07-08
categories = []
draft = true
summary = """
"""
+++

```bash
curl -s https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt | awk -F ';' '{ if(length($2) > 0 && $2 != "<control>") print $1, length($2), $2; else print $1, length($11), $11 }' | sort -rnk2 >| sorted.txt
```


