+++
title = "Querying the unicode database"
date = 2019-08-17
categories = ["unicode"]
draft = true
summary = """
Am I allowed to call it a database if it's just a giant text file?"""
+++

In [a previous post]({{< ref "building-python-strings-using-character-names"
>}})

```bash
curl -s https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt | awk -F ';' '{ if(length($2) > 0 && $2 != "<control>") print $1, length($2), $2; else print $1, length($11), $11 }' | sort -rnk2 >| sorted.txt
```


