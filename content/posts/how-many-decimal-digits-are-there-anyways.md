+++
title = "How many decimal digits are there, anyways?"
date = "2018-12-25"
categories = ["ios"]
draft = true
+++

Recently I was reviewing a PR opened by a colleague of mine and noticed a function like the following:

```objc
+ (BOOL)validateNumber:(NSString *)number {
    NSCharacterSet *invertedDecimalDigitCharacterSet = 
        [[NSCharacterSet decimalDigitCharacterSet] invertedSet];
    NSRange range = [number rangeOfCharacterFromSet:invertedDecimalDigitCharacterSet];
    // Ensure that the given string is digits only
    return range.location == NSNotFound
}
```

On a hunch, I checked the [docs for `decimalDigitCharacterSet`][decimalDigitCharacterSet]:

> A character set containing the characters in the category of Decimal Numbers. … Informally, this set is the set of all
> characters used to represent the decimal values 0 through 9. These characters include, for example, the decimal digits
> of the Indic scripts and Arabic.

That's definitely going to be trouble. `validateNumber` is supposed to return `YES` only when the input string is made
up of the decimal digits 0 through 9, but `decimalDigitCharacterSet` includes every character in the Unicode category
Nd, also known as Decimal_Number ([see the full list of categories here][categories]). Let's try a few:

```swift
let s = CharacterSet.decimalDigits

// U+0031 DIGIT ONE
s.contains("1")  // true as expected

// U+1D7D9 MATHEMATICAL DOUBLE-STRUCK DIGIT ONE
s.contains("𝟙")  // true!

// U+0967 DEVANAGARI DIGIT ONE
s.contains("१")  // true!

// U+1811 MONGOLIAN DIGIT ONE
s.contains("᠑")  // true!
```

Note that for convenience I'm using Swift's CharacterSet, which is bridged to `NSCharacterSet`, so observations about
it apply equally to its Objective-C counterpart. 

Clearly this isn't doing what my colleague intended. Just how many of these Nd characters are there? It seems like we
ought to be able to simply ask the `CharacterSet` how many elements it has with `count`, but it doesn't conform to
`Collection`, nor does `NSCharacterSet` support any simple means of obtaining the number of characters represented, so
we'll just have to do it the hard way:

```swift
import Foundation

func sizeOf(set: CharacterSet) -> Int {
    return (0...Int(0x10FFFF))
        .compactMap { Unicode.Scalar($0) }
        .filter { set.contains($0) }
        .count
}

let s = CharacterSet.decimalDigits
print(sizeOf(set: s))  // 610
```

`sizeOf(set:)` enumerates every code point from zero to the maximum valid value, 0x10FFFF, and checks whether each value
is in the set. `compactMap` lets us ignore cases where `Unicode.Scalar` returns `nil`, as it does in the range 0xD800 to
0xDFFF, because these are invalid code points reserved for use as surrogates in UTF-16 (incidentally, UTF-16 is also the
reason that 0x10FFFF is the maximum valid code point).

According to this function, then, there are not just ten decimal number characters, as you might expect, but _six 
hundred_ and ten! To fix the bug, we'll just have to be more explicit:

```objc
+ (BOOL)validateAccountNumber:(NSString *)number {
    NSCharacterSet *invertedArabicDecimalDigitCharacterSet = 
        [[NSCharacterSet characterSetWithCharactersInString:@"0123456789"] invertedSet];
    NSRange range = [number rangeOfCharacterFromSet:invertedArabicDecimalDigitCharacterSet];
    // Ensure that the given string is digits only
    return range.location == NSNotFound
}
```

Amusingly, the [accepted answer for this question on Stack Overflow][so-answer] also gets this wrong. I can hardly blame
them!

[decimalDigitCharacterSet]: https://developer.apple.com/documentation/foundation/nscharacterset/1408239-decimaldigitcharacterset?language=objc
[categories]: https://www.unicode.org/reports/tr44/#General_Category_Values
[nd-length]: https://www.compart.com/en/unicode/category/Nd
[so-answer]: https://stackoverflow.com/a/6091456/1292061