+++
title = "NaN-boxing in Go"
date = 2020-06-07
categories = ["go", "ieee754"]
summary = """
NaNs have bits to spare; why not use them?"""
+++

Recently, I was reading [this Go
proposal](https://github.com/golang/go/issues/20660) to disallow NaN keys in
maps whose keys are floating-point values. The proposal and accompanying
discussion are interesting in their own right, as is the [blog
post](https://research.swtch.com/randhash) to which it also links. While
reading, I went to refresh my understanding of the structure of [IEEE 754
floating-point values](https://en.wikipedia.org/wiki/IEEE_754), and in
particular how the "special cases" of ±infinity and NaN are handled.

For 32-bit IEEE 754 floats, one bit is used as the sign bit, eight bits are used
for the exponent, and the remaining twenty-three bits are used for the
significand, also know as the mantissa:

```text
1    8                23
s eeeeeeee mmmmmmmmmmmmmmmmmmmmmmm
↑   exp            mantissa
|
sign bit
```

64-bit floats are similar, with one bit for the sign, eleven bits for the
exponent, and 52 bits for the significand. The special cases of ±infinity and
NaN are represented by setting the exponent to all-ones. Then, the significand
indicates the case. An all-zeros significand represents infinity, with sign
controlled by the sign bit. Any other value in the significand represents NaN,
with the most significant bit of the significand distinguishing between a quiet
NaN and a signaling NaN. This means that there are 2^23-1 representations of NaN
for a 32-bit float, and 2^52-1 for a 64-bit float! This is not an oversight in
the specification; instead, these extra bits are intended to be used as a
payload to indicate what went wrong in the preceding calculation that caused the
result to be NaN. However, we can instead misuse these bits to store arbitrary
data, a technique referred to as NaN-boxing, and is well-known. For example,
Mozilla's SpiderMonkey JS interpreter [uses
it](https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey/Internals),
and [here's some discussion on
why](https://softwareengineering.stackexchange.com/q/185406/94352). Naturally,
it's also possible to implement in Go:

```go
package main

import (
	"fmt"
	"math"
)

func main() {
	e := encode("Hello world!")
	fmt.Println(e)
	d := decode(e)
	fmt.Println(d)
}

func encode(s string) []float64 {
	f := make([]float64, len(s))
	for i, c := range s {
		f[i] = math.Float64frombits(math.Float64bits(math.NaN()) & ^uint64(1<<8-1) | uint64(uint8(c)))
	}
	return f
}

func decode(f []float64) string {
	b := make([]rune, len(f))
	for i, c := range f {
		b[i] = rune(math.Float64bits(c) & uint64(1<<8-1))
	}
	return string(b)
}
```

Running this prints:

```text
[NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN]
Hello world!
```

You can try it yourself [here](https://play.golang.org/p/stHTwH1rgjo). This is a
pretty naive implementation, with at least the following faults:

- It only encodes one ASCII character per float64, wasting a lot of space
- It silently encodes characters beyond ASCII incorrectly, since it simply
  truncates everything beyond the first byte
- It cannot encode `0x00`, because that would be positive infinity

All of these are solvable, of course, but this is just an example. For a more
thorough, full-featured implementation of NaN-boxing in C, check out [this
project](https://github.com/zuiderkwast/nanbox).
