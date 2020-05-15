+++
title = "Eavesdropping on SLAAC (part 1)"
date = 2020-05-15
categories = ["networking"]
draft = true
summary = """
How many addresses does one host need?"""
+++

One of the many cool features of IPv6 is stateless address auto-configuration,
SLAAC. SLAAC, as the name suggests, is a mechanism for hosts to statelessly
configure their own IPv6 addresses. SLAAC has a lot of complexities and nuances,
and is defined and modified in a pile of RFCs, linked at the [bottom of this
article](#resources). Here, though, I just want to observe a real device — my
iPhone — executing SLAAC, and won't try to offer a comprehensive treatment of
the whole protocol. A bit of explanation will still be helpful, though. Here's a
simplified view of the steps my device takes when it connects to WiFi:

1. Generate a tentative link-local IP address
1. Check the tentative link-local IP address for conflicts on the link
1. Solicit a router advertisement
1. Process the router's advertisement to determine the SLAAC prefix and address
   lifetimes
1. Generate one tentative temporary and one tentative secured IP address
1. Check the two tentative addresses for conflicts

The entire exchange occurs in five ICMPv6 packets. I'll copy textual
representations of the packets here, but if you want to open the capture
yourself and follow along, you can download it [here](slaac.pcapng). Despite
only taking a fraction of a second, the semantics are not straightforward, so
I'll break this up over a couple posts.

_Let's watch!_

##### Generate and DAD the link-local address

First, the device generates its link-local address. It does this starting with
the 64-bit [link-local prefix](https://tools.ietf.org/html/rfc4291#page-11),
`fe80::/64`, then generating a semantically opaque (aka "secured") interface
identifier for the final 64 bits of the address. The process for generating the
secure interface identifier is basically to take a bunch of machine-specific
data such as the MAC address, a network ID, a counter, a secret key, and
possibly other items, and cryptographically hash them together. It's specified
fully in [RFC 7217](https://tools.ietf.org/html/rfc7217#page-7). As we'll see,
in this case the device generated `fe80::14a4:8e99:8a23:c37b` as its link-local
address. Before this address can be truly assigned and used as preferred
address, though, the device must ensure it's unique on the link, and so it
performs duplicate address detection, or DAD, by sending out the following
packet.

```text
Ethernet II, Src: Apple_b1:04:da (b8:5d:0a:b1:04:da), Dst: IPv6mcast_ff:23:c3:7b (33:33:ff:23:c3:7b)
    Destination: IPv6mcast_ff:23:c3:7b (33:33:ff:23:c3:7b)
    Source: Apple_b1:04:da (b8:5d:0a:b1:04:da)
    Type: IPv6 (0x86dd)
Internet Protocol Version 6, Src: ::, Dst: ff02::1:ff23:c37b
Internet Control Message Protocol v6
    Type: Neighbor Solicitation (135)
    Code: 0
    Checksum: 0x7c05 [correct]
    [Checksum Status: Good]
    Reserved: 00000000
    Target Address: fe80::14a4:8e99:8a23:c37b
    ICMPv6 Option (Nonce)
```

This is a short packet, but there's a lot to unpack. Let's start at the
highest-level protocol, ICMPv6, listed here last. Type 135, code 0 means
neighbor solicitation, as Wireshark helpfully identifies. For neighbor
solicitation, the ICMPv6 target address indicates the address that the sender
would like to identify. That is, the sender of this packet would like to find
out who, if anyone, currently holds the address `fe80::14a4:8e99:8a23:c37b`. If
someone does hold that address, it should respond with a neighbor advertisement
saying so. Note that `fe80::14a4:8e99:8a23:c37b` is the link-local address the
device generated earlier, and is now trying to ensure is unique.

Next is the IPv6 layer. The only two interesting pieces here are the source and
destination IP addresses: `::` and `ff02::1:ff23:c37b`, respectively. `::` is
the [unspecified address](https://tools.ietf.org/html/rfc4291#page-9),
indicating that the sender does not yet have a usable address. It can't put
`fe80::14a4:8e99:8a23:c37b` here, because that address has not yet been
confirmed to be unique. The destination address, meanwhile, is a [solicited-node
multicast address](https://tools.ietf.org/html/rfc4291#page-16). This address is
interesting: it is constructed by appending the low-order 24 bits from a
solicited nodes address to the prefix `ff02:0:0:0:0:1:ff00:0/104`. In this case,
the device is soliciting `fe80::14a4:8e99:8a23:c37b`, so it appends `23:c37b` to
the prefix to obtain `ff02::1:ff23:c37b`. Because hosts are required to join
the solicited-node multicast groups corresponding to each of their addresses, my
device can be sure that if another host on the link has
`fe80::14a4:8e99:8a23:c37b`, it will be part of `ff02::1:ff23:c37b` and will
receive the neighbor solicitation.

Finally, let's examine the Ethernet frame. The source is uninteresting; it's
simply the unicast MAC address of my device's interface. The destination,
though, is similar in spirit to the solicited-node multicast address in the IP
destination field. In fact, you might recognize some bytes in common!
`33:33:ff:23:c3:7b` is an Ethernet [IPv6 multicast
address](https://tools.ietf.org/html/rfc2464#page-5). That address is formed by
appending the low-order 32 bits from the destination multicast IPv6 address to
the prefix `33:33`. Since the destination address is `ff02::1:ff23:c37b`, the
MAC address is `33:33:ff:23:c3:7b`. This frame will therefore be broadcast to
all hosts on the link, but only hosts with matching IP addresses (there can be
more than one, since only three bytes from the IP address appear in the MAC
address!) will have configured their Ethernet interfaces to accept the frame. As
a further optimization, MLD-snooping switches on the link can avoid flooding the
frame to ports they know do not connect to members of the multicast. Contrast
this with IPv4's ARP, in which address resolution frames are always sent to the
all-hosts MAC broadcast address `ff:ff:ff:ff:ff:ff`, and hosts receive and must
process every ARP request, and you can see why the extra complexity is worth it.

So, to summarize this packet, the device is asking each host on the link to
please reply with a neighbor advertisement if that host has the address
`fe80::14a4:8e99:8a23:c37b`, which the device would like to assign to itself.
Because the device receives no such advertisement, DAD completes successfully,
and the device assigns itself the link-local address
`fe80::14a4:8e99:8a23:c37b`. This is by far the more likely case, since the
chosen link-local address contains 64 bits of pseudorandom data, making it
exceedingly unlikely that another host already holds this same address. In fact,
DAD is so likely to succeed that [RFC 4429](https://tools.ietf.org/html/rfc4429)
allows a host to assume it _has_ succeeded (for certain purposes) before it
does!

But a link-local address is of limited utility. Though it is required by the
specification, packets from a link-local address cannot be routed, meaning they
cannot leave the link on which they are originally sent! Translation: no
internet access. In part 2, we'll see the device generate its globally unique
routable addresses so that it can communicate with the world.

### Resources

- [RFC 4862](https://tools.ietf.org/html/rfc4862) is the overall RFC for basic
  SLAAC functionality
- [RFC 4443](https://tools.ietf.org/html/rfc4443) describes ICMPv6, the IPv6
  protocol which is used for all SLAAC communications
- [RFC 4861](https://tools.ietf.org/html/rfc4861) specifies the wire formats of
  various SLAAC-related ICMPv6 message types
- [RFC 4941](https://tools.ietf.org/html/rfc4941) describes temporary address
  generation
- [RFC 7217](https://tools.ietf.org/html/rfc7217) describes semantically opaque
  ("secured") address generation
- [RFC 4429](https://tools.ietf.org/html/rfc4429) describes modifications to DAD
  to reduce the time it takes, called "optimistic DAD"
- [RFC 4291](https://tools.ietf.org/html/rfc4291) defines various special
  address ranges, such as the unspecified address, link-local addresses, and
  multicast addresses
- [RFC 2464](https://tools.ietf.org/html/rfc2464) elaborates on transmission of
  IPv6 traffic over an Ethernet link layer

