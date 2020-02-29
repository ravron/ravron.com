+++
title = "Go 1.14: testing's new T.Cleanup"
date = 2020-02-29
categories = ["go", "testing"]
summary = """
Last-in, first-out execution of a list of functions? Hey, that sounds familiar…"""
+++

Go 1.14 was [recently released](https://blog.golang.org/go1.14). The release
notes include [one change](https://golang.org/doc/go1.14#testing) to the
ubiquitous `testing` library:

> The testing package now supports cleanup functions, called after a test or
> benchmark has finished, by calling `T.Cleanup` or `B.Cleanup` respectively.

And the docs offer just a [bit more](https://golang.org/pkg/testing/#T.Cleanup):

> Cleanup registers a function to be called when the test and all its subtests
> complete. Cleanup functions will be called in last added, first called order.

How might this new behavior be implemented? My first thought was pretty
straightforward: a slice of niladic functions to which each new cleanup function
is appended and whose contents are executed one-by-one in reverse order after
the test function returns. That would look something like this:

```go
struct T {
	// other fields...
	cleanups []func()

func (*t T) Cleanup(f func ()) {
	t.cleanups = append(t.cleanups, f)
}

// runTest is the imaginary function that actually invokes the test function
// fn.
func (*t T) runTest(fn func(t *T)) {
	// other setup...

	fn(t)

	for i := len(t.cleanups) - 1; i >= 0; i-- {
		t.cleanups[i]()
	}
}
```

Note that this is greatly oversimplified, since I've omitted handling for panics
and parallel testing, both of which add considerable complexity. Thinking about
the behavior I've implemented, though, you might notice something intriguing:
the cleanup functionality is first-in, last-out, just like a classic stack data
structure. What's more, the sole purpose of the cleanup functionality is to jump
to functions, one after another, in this LIFO order. Putting it like that, the
behavior we need is exactly what the classic call stack does!

There's just one problem, though – we don't want to call the cleanup functions
immediately, as they're registered, but later, after the test function returns.
We really need some way to… _defer_ them! Go has a tool that does just this, the
`defer` keyword, which pushes a function onto a stack for execution later. This
is exactly how `T.Cleanup` is [actually
implemented](https://golang.org/src/testing/testing.go?s=26798:26832#L771):

```go
func (t *T) Cleanup(f func()) {
	oldCleanup := t.cleanup
	t.cleanup = func() {
		if oldCleanup != nil {
			defer oldCleanup()
		}
		f()
	}
}
```

Again, I've elided some irrelevant details. After a test function returns (or
ends early with [`T.FailNow`](https://golang.org/pkg/testing/#T.FailNow), or
panics), `testing` invokes `t.cleanup`, and all of the cleanup functions
previously registered get run in LIFO order, as promised.

I found it a little difficult to visualize how exactly control gets passed
through multiple cleanup functions, so here's a concrete example. Imagine we
register three cleanup functions, `A`, `B`, and `C`:

```go
func TestFoo(t *testing.T) {
	t.Cleanup(A)
	t.Cleanup(B)
	t.Cleanup(C)
	// rest of your test...
}
```

Later, when the `testing` package invokes `t.cleanup`, the series of calls looks
like this:

1. `testing` calls `cC`, the function literal that closed over `C`
1. `cC` `defer`s `cB`, the function literal that closed over `B`
1. `cC` invokes `C`
1. After `cC` returns, the deferred `cB` is invoked by the runtime
1. `cB` `defer`s `cA`, the function literal that closed over `A`
1. `cB` invokes `B`
1. After `cB` returns, the deferred `cA` is invoked by the runtime
1. `cA` invokes `A`

Why is this better than the straightforward `[]func()` solution from before?
Well, beside having a certain elegance to it, the use of `defer` means that
panics in any of the cleanup functions will be handled in mostly the same way
that panics during the test function itself would be, and can share recovery and
reporting machinery.

_Bonus: In Go 1.14, `defer` also got a lot faster. The
[spec](https://github.com/golang/proposal/blob/master/design/34481-opencoded-defers.md)
for that optimization is pretty engaging, and the graph is impressive:_

{{< figure
src="go-defer-benchmark.jpeg"
caption="With Go 1.14, the overhead of most uses of `defer` is nearly the same as a normal function call."
alt="Benchmark showing defer's overhead to be nearly the same as a normal function call"
attr="Image from @janiszt"
attrlink="https://twitter.com/janiszt/status/1215601972281253888"
>}}
