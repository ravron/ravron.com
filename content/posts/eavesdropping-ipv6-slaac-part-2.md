+++
title = "Eavesdropping on SLAAC (part 2)"
date = 2020-05-25
categories = ["networking"]
summary = """
It's time to talk to the router."""
+++

In [part 1]({{< ref "eavesdropping-ipv6-slaac-part-1" >}}), we watched my device
execute the first couple of steps of stateless address auto-configuration,
generating a link-local address and ensuring its uniqueness on the link. As I
concluded that post, while it is an important step for SLAAC, the link-local
address is of limited utility for actual data transfer, since traffic
originating from it will be dropped by the router at the edge of my local
network. To be able to communicate with the rest of the world, my device now
needs to secure at least one address with global scope.

### Solicit a router advertisement

So far, my iPhone has been able to proceed without help from other network
resources, but it now needs to ask for help from the local router. It needs a
router advertisement (RA) ICMPv6 packet, which contains details that will allow
my device to continue SLAAC. Routers send out RAs periodically, usually every
minute or two, but devices can also send a router solicitation packet (RS) to
request an immediate advertisement ahead of schedule, and that's exactly what my
device does.

```text
Ethernet II, Src: Apple_b1:04:da (b8:5d:0a:b1:04:da), Dst: IPv6mcast_02 (33:33:00:00:00:02)
    Destination: IPv6mcast_02 (33:33:00:00:00:02)
    Source: Apple_b1:04:da (b8:5d:0a:b1:04:da)
    Type: IPv6 (0x86dd)
Internet Protocol Version 6, Src: fe80::14a4:8e99:8a23:c37b, Dst: ff02::2
Internet Control Message Protocol v6
    Type: Router Solicitation (133)
    Code: 0
    Checksum: 0x8c5a [correct]
    [Checksum Status: Good]
    Reserved: 00000000
```

There's not a whole lot to analyze here. As before, let's start at the
highest-level protocol, ICMPv6, listed here last. Type 133, code 0 indicates
that this packet is a router solicitation. Router solicitations don't include
any other data, so that's all there is to see at the ICMPv6 layer.

The IPv6 headers are similarly unsurprising. The source is my device's
newly-minted link-local address from [part 1]({{< ref
"eavesdropping-ipv6-slaac-part-1" >}}), while the destination is the
[all-routers address](https://tools.ietf.org/html/rfc4291#page-16) with
link-local scope, `ff02::2`, indicating that my device wants to multicast to any
routers on the link. In my case, there is just one, but the protocol works just
the same with multiple.

Finally, the Ethernet layer. The source is my device's MAC address, while the
destination is an IPv6 multicast address, used in just the same way as we saw in
part 1 during duplicate address detection for the link-local address.

After my network's router receives this RS, it responds promptly with an
advertisement.

### Process the router advertisement

```text
Ethernet II, Src: Ubiquiti_24:47:7e (b4:fb:e4:24:47:7e), Dst: IPv6mcast_01 (33:33:00:00:00:01)
    Destination: IPv6mcast_01 (33:33:00:00:00:01)
    Source: Ubiquiti_24:47:7e (b4:fb:e4:24:47:7e)
    Type: IPv6 (0x86dd)
Internet Protocol Version 6, Src: fe80::b6fb:e4ff:fe24:477e, Dst: ff02::1
Internet Control Message Protocol v6
    Type: Router Advertisement (134)
    Code: 0
    Checksum: 0xf7b1 [correct]
    [Checksum Status: Good]
    Cur hop limit: 64
    Flags: 0x08, Prf (Default Router Preference): High
    Router lifetime (s): 1800
    Reachable time (ms): 0
    Retrans timer (ms): 0
    ICMPv6 Option (Prefix information : 2607:f598:b58a:2e0::/64)
    ICMPv6 Option (Recursive DNS Server fdda:faa8:2d53:9f86::)
    ICMPv6 Option (DNS Search List Option local)
    ICMPv6 Option (Source link-layer address : b4:fb:e4:24:47:7e)
```

As expected, the ICMPv6 type is 134, a router advertisement. Following that, the
advertisement contains a bunch of information that will help my device configure
itself. Some of that information is in predefined fields in the RA, while others
are provided as ICMPv6 options. Though these ICMPv6 message types are defined in
[RFC 4861](https://tools.ietf.org/html/rfc4861), you'll find only a few of these
options are documented there, because many new options were added after that
RFC's completion, as allowed by RFC 4861 itself. Check the [IANA's
site](https://www.iana.org/assignments/icmpv6-parameters/icmpv6-parameters.xhtml#icmpv6-parameters-5)
for an up-to-date list of ICMPv6 ND options and the RFCs that describe them.

So what is all this information?

- Hop limit of 64: the router is asking hosts to start their hop counters at 64.
  The hop-by-hop IPv6 header replaces TTL functionality from IPv4.
- Flags `0x08`: the values here are defined in [RFC
  5175](https://tools.ietf.org/html/rfc5175#page-2). These are notable both for
  what flags _are_ set, as well as which are not. The first, unset bit is the
  "managed" bit. When set, it indicates that hosts should use DHCPv6 — roughly
  equivalent to IPv4's DHCP — to ask for address allocations, rather than SLAAC.
  The second, also unset bit is the "other configuration" bit, which indicates
  that even if hosts may use SLAAC to configure an address, other information is
  available via DHCPv6. Since neither is set, my device knows it may use SLAAC
  to configure addresses, and that there's no need to send any DHCPv6 queries
  for additional information. Finally, the single set bit indicates the sender
  of this packet is has a router preference of "high." On my network, this is
  irrelevant, since there's just one router, but on a multi-router network,
  router preference can indicate to which router a host should try to send its
  traffic first.
- Router lifetime of 1800s: how long the host should consider this router valid
  as a default route. Because the router periodically transmits RAs with a
  shorter period than this value, the router should always be the default route
  unless it becomes unreachable.
- Reachable and retransmit timers of 0: these values are parameters for the
  neighbor discovery algorithms. When set to zero, as they are here, the router
  is indicating that they are unspecified, and hosts should use default values.
- Prefix of `2607:f598:b58a:2e0::/64`: this is the most important information
  for our purposes, so I'll discuss it below.
- DNS server `fdda:faa8:2d53:9f86::`: this is the address that hosts should use
  for DNS resolution. I've manually configured my router with this address. It's
  a [unique local address](https://tools.ietf.org/html/rfc4193) which I
  generated and manually assigned to my raspberry pi running
  [Pi-hole](https://pi-hole.net/). That's a story for another post, though!
- DNS search list `local`: this defines a TLD that hosts should use for mDNS,
  aka Bonjour.
- Source link-layer address `b4:fb:e4:24:47:7e`: this is the MAC address of my
  router, and allows hosts to populate their ND cache accordingly.

Most of this information isn't relevant for SLAAC, but the prefix information is
key. A prefix of `2607:f598:b58a:2e0::/64` indicates that my ISP has assigned my
router this entire block of addresses. My router can hand out any addresses it
likes, or my hosts can self-assign them, as long as they start with this prefix.

Take a moment to consider what that means! IPv6's address space is so vast that
my ISP has casually handed my router 2^64 (18,446,744,073,709,551,616) addresses
with which it can do whatever it wants. In fact, the ISP actually gave my router
a /60 prefix, but SLAAC requires a /64 prefix, so my router has chosen to use
the first of sixteen separate address blocks, each containing 2^64 addresses.
And this is standard practice! Incredible.

### Generate and DAD global addresses

Finally, my device has everything it needs to generate usable global addresses.
Global address generation proceeds similarly to link-local address generation,
except that it uses the prefix provided in the RA, `2607:f598:b58a:2e0::/64`,
rather than the well-known link-local prefix `fe80::/10`. One remaining question
is which method my device will use to generate its interface identifier, the
final 64 bits of its address. One option is to use a stable, semantically opaque
identifier per [RFC 7217](https://tools.ietf.org/html/rfc7217#page-7), as it did
for the link-local address. Another option is generate a temporary address per
[RFC 4941](https://tools.ietf.org/html/rfc4941). The details of the distinction
between these two are interesting, but a bit of a digression.

Thankfully, with IPv6, there's no need to choose — why not both? Because it is
perfectly normal for an interface to have many addresses, this is exactly what
my device does here, generating one semantically opaque, or "secured," address,
`2607:f598:b58a:2e0:10d7:cdb3:8b6c:b834`, and one temporary address,
`2607:f598:b58a:2e0:1da0:19cd:3bbc:f407`. Notice that, as required, each of
these addresses uses the 64 bit prefix specified in the RA.

Finally, my device must ensure that that both of these generated addresses are
in fact unique. This uses exactly the same DAD algorithm described in part 1, so
I'll just display the associated ICMPv6 packets here without further
comment.

```text
Ethernet II, Src: Apple_b1:04:da (b8:5d:0a:b1:04:da), Dst: IPv6mcast_ff:6c:b8:34 (33:33:ff:6c:b8:34)
    Destination: IPv6mcast_ff:6c:b8:34 (33:33:ff:6c:b8:34)
    Source: Apple_b1:04:da (b8:5d:0a:b1:04:da)
    Type: IPv6 (0x86dd)
Internet Protocol Version 6, Src: ::, Dst: ff02::1:ff6c:b834
Internet Control Message Protocol v6
    Type: Neighbor Solicitation (135)
    Code: 0
    Checksum: 0xd0fc [correct]
    [Checksum Status: Good]
    Reserved: 00000000
    Target Address: 2607:f598:b58a:2e0:10d7:cdb3:8b6c:b834
    ICMPv6 Option (Nonce)

Ethernet II, Src: Apple_b1:04:da (b8:5d:0a:b1:04:da), Dst: IPv6mcast_ff:bc:f4:07 (33:33:ff:bc:f4:07)
    Destination: IPv6mcast_ff:bc:f4:07 (33:33:ff:bc:f4:07)
    Source: Apple_b1:04:da (b8:5d:0a:b1:04:da)
    Type: IPv6 (0x86dd)
Internet Protocol Version 6, Src: ::, Dst: ff02::1:ffbc:f407
Internet Control Message Protocol v6
    Type: Neighbor Solicitation (135)
    Code: 0
    Checksum: 0xe4ef [correct]
    [Checksum Status: Good]
    Reserved: 00000000
    Target Address: 2607:f598:b58a:2e0:1da0:19cd:3bbc:f407
    ICMPv6 Option (Nonce)
```

### Assign address and mark as valid

Because my device receives no neighbor advertisement in response to its DAD, it
concludes its tentative global addresses are in fact unique, and assigns them to
the interface, which means SLAAC has successfully completed, and my device is
ready to communicate with the world! You can see all of the interface's IPv6
addresses below, listed on lines starting with `inet6`.

```text
$ ifconfig en0
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
	options=400<CHANNEL_IO>
	ether 8c:85:90:7a:49:c0
	inet6 fe80::14a4:8e99:8a23:c37b%en0 prefixlen 64 secured scopeid 0x5
	inet 192.168.1.15 netmask 0xffffff00 broadcast 192.168.1.255
	inet6 2607:f598:b58a:2e0:10d7:cdb3:8b6c:b834 prefixlen 64 autoconf secured
	inet6 2607:f598:b58a:2e0:1da0:19cd:3bbc:f407 prefixlen 64 autoconf temporary
	nd6 options=201<PERFORMNUD,DAD>
	media: autoselect
	status: active
```

While there is evidently considerable complexity involved in getting usable
addresses, the process typically takes a fraction of a second and requires no
user involvement or complex configuration. It's also worth pointing out that we
can now see what's "stateless" about SLAAC: my router has no reservation or
table entry corresponding to my device. This is a worthwhile improvement over
DHCP on its own. Overall, SLAAC means IPv6 address configuration is fast,
resilient, and flexible, making it the go-to choice when considering how to set
up your own IPv6 network.
