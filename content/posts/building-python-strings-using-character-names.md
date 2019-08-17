+++
title = "Building python strings using character names"
date = 2019-07-14
categories = ["python", "unicode"]
summary = """
Presumably someone, somewhere found this useful."""
+++

I was perusing the [Python 3 language
reference](https://docs.python.org/3/reference/index.html) and found something
pretty surprising in the lexical analysis [section about string
literals](https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals).
There's a table there that lists valid escape sequences in Python strings, and
all the usual suspects are there: `\'` to escape an apostrophe that would
otherwise end the literal, `\n` to embed a newline, and even `\uxxxx` and
`\Uxxxxxxxx` to identify Unicode code points with two or four bytes
respectively. These are familiar to most people with programming experience.

One of the escape sequences Python permits, though, is quite unusual. The
documentation says that the escape sequence `\N{name}` means "character named
`name` in the Unicode database." I've never seen a `\N{…}` escape sequence
before. Let's try it!

```python
>>> '\N{COLON}'
':'
>>> '\N{DIGIT EIGHT}'
'8'
>>> '\N{LATIN CAPITAL LETTER B}'
'B'
```

Sure enough, it works as advertised. That's still pretty tame though, let's try
a few more.

```python
>>> '\N{LATIN LETTER SMALL CAPITAL L}'
'ʟ'
>>> '\N{NO ONE UNDER EIGHTEEN SYMBOL}'
'🔞'
>>> '\N{HALFWIDTH HANGUL LETTER SSANGTIKEUT}'
'ﾨ'
>>> '\N{GREEK SMALL LETTER ALPHA WITH DASIA AND PERISPOMENI}'
'ἇ'
>>> '\N{GREATER-THAN ABOVE LESS-THAN ABOVE DOUBLE-LINE EQUAL}'
'⪒'
>>> '\N{MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING UP AND LEFT}'
'⦩'
>>> '\N{DOWNWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT}'
'⥥'
>>> '\N{ARABIC LIGATURE UIGHUR KIRGHIZ YEH WITH HAMZA ABOVE WITH ALEF MAKSURA ISOLATED FORM}'
'ﯹ'
```

To be honest, I have no idea why this functionality exists in the language, but
I must say it's pretty entertaining. Of course, there's only one thing to do
now:

```python
import sys
import unicodedata

if __name__ == '__main__':
    result = "'"
    for c in sys.argv[1]:
        try:
            result += f'\\N{{{unicodedata.name(c)}}}'
        except ValueError:
            result += c
    result += "'"
    print(result)
```

This script accepts an input string and prints the Python string that results by
replacing each code point with its `\N{…}` escape sequence.

```
$ python expander.py 'François, Heßler, Noël, and Борис are all here! 👨‍👨‍👧‍👦'
'\N{LATIN CAPITAL LETTER F}\N{LATIN SMALL LETTER R}\N{LATIN SMALL LETTER
A}\N{LATIN SMALL LETTER N}\N{LATIN SMALL LETTER C WITH CEDILLA}\N{LATIN SMALL
LETTER O}\N{LATIN SMALL LETTER I}\N{LATIN SMALL LETTER
S}\N{COMMA}\N{SPACE}\N{LATIN CAPITAL LETTER H}\N{LATIN SMALL LETTER E}\N{LATIN
SMALL LETTER SHARP S}\N{LATIN SMALL LETTER L}\N{LATIN SMALL LETTER E}\N{LATIN
SMALL LETTER R}\N{COMMA}\N{SPACE}\N{LATIN CAPITAL LETTER N}\N{LATIN SMALL LETTER
O}\N{LATIN SMALL LETTER E WITH DIAERESIS}\N{LATIN SMALL LETTER
L}\N{COMMA}\N{SPACE}\N{LATIN SMALL LETTER A}\N{LATIN SMALL LETTER N}\N{LATIN
SMALL LETTER D}\N{SPACE}\N{CYRILLIC CAPITAL LETTER BE}\N{CYRILLIC SMALL LETTER
O}\N{CYRILLIC SMALL LETTER ER}\N{CYRILLIC SMALL LETTER I}\N{CYRILLIC SMALL
LETTER ES}\N{SPACE}\N{LATIN SMALL LETTER A}\N{LATIN SMALL LETTER R}\N{LATIN
SMALL LETTER E}\N{SPACE}\N{LATIN SMALL LETTER A}\N{LATIN SMALL LETTER L}\N{LATIN
SMALL LETTER L}\N{SPACE}\N{LATIN SMALL LETTER H}\N{LATIN SMALL LETTER E}\N{LATIN
SMALL LETTER R}\N{LATIN SMALL LETTER E}\N{EXCLAMATION
MARK}\N{SPACE}\N{MAN}\N{ZERO WIDTH JOINER}\N{MAN}\N{ZERO WIDTH
JOINER}\N{GIRL}\N{ZERO WIDTH JOINER}\N{BOY}'
```

So much more readable, don't you agree?
