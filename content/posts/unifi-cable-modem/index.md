+++
title = "Working around an unhelpful cable modem with UniFi"
date = 2020-11-14
categories = ["networking", "unifi"]
summary = """
A lot of extra effort because my modem has bad ARP etiquette"""
+++

The router at the edge of my home network is an [UniFi Security Gateway
three-port](https://www.ui.com/unifi-routing/usg/), or just USG. It has two WAN
ports, which can be configured so that WAN1 is the primary and WAN2 is used as
failover only. Like other home networking enthusiasts, I've set up an LTE modem
— in my case, a [Netgear
LB1120](https://www.netgear.com/home/products/mobile-broadband/lte-modems/LB1120.aspx)
— on WAN2 with a cheap 2GB/mo. prepaid data plan from T-Mobile. The USG switches
over to WAN2 relatively quickly when it's unable to ping a test host from WAN1.

Of course, I occasionally want to configure the LB1120, which has the usual
self-hosted configuration web server. Because it doesn't serve as a DHCP server,
just a bridge to the LTE network's DHCP servers, it's a little tricky to talk to
it. The gist is that it has a hardcoded
[RFC1918](https://tools.ietf.org/html/rfc1918#section-3) private IPv4 address,
`192.168.5.1`, which works even when the device is in bridge mode. Because the
modem is outside my home LAN, though, getting to it requires some clever
configuration on the USG involving a pseudo-ethernet interface and NAT
masquerading. Thankfully, [Owen Nelson's excellent blog
post](https://owennelson.co.uk/accessing-a-modem-through-a-ubiquiti-usg/) on
exactly this topic made it easy, and I was able to get [a working
configuration](https://github.com/ravron/unifi/commit/c46ea48f4157b3bdd5693550fe5bd271f9f377c2#diff-65c9fe36cffa3ad97c0f1bc1c5754aa7eb8bd76bd757aa4097775b2986c1c6a6)
without too much trouble:

```json
{
  "interfaces": {
    "pseudo-ethernet": {
      "peth0": {
        "address": [
          "192.168.5.2/24"
        ],
        "description": "Access to LTE modem",
        "link": "eth2"
      }
    }
  },
  "service": {
    "nat": {
      "rule": {
        "5000": {
          "description": "Access to LTE modem",
          "destination": {
            "address": "192.168.5.1"
          },
          "outbound-interface": "peth0",
          "type": "masquerade"
        }
      }
    }
  }
}
```

While I recommend reading Owen's blog post, linked above, for the details of
what this configuration does, I can summarize briefly. The `interfaces` section
configures a new pseudo-ethernet interface named `peth0` that will be linked to
the physical `eth2` interfaces, corresponding to WAN2. The pseudo-ethernet
interface has its own IP address and subnet mask, and to avoid conflicts with
the physical interface that hosts it, it also uses a new, synthetic MAC address.
Meanwhile, the `service` section configures NAT so that traffic outbound on the
`peth0` interface will have its source IP address rewritten to that of the
interface. For even more information, I recommend [the documentation on UniFi's
`config.gateway.json`
files](https://help.ui.com/hc/en-us/articles/215458888-UniFi-USG-Advanced-Configuration-Using-config-gateway-json),
and the [documentation for
Vyatta](http://0.us.mirrors.vyos.net/vyatta/vc6.5/docs/Vyatta-Documentation_6.5R1_v01/),
the sort-of open-source base on which UniFi is built.

In September, I got a new cable modem for the primary uplink on WAN1, an [Arris
SB8200](https://www.surfboard.com/products/cable-modems/sb8200/), and wanted to
set things up just the same way. I figured I could use exactly the same
strategy, and
[added](https://github.com/ravron/unifi/commit/291d01357840d33b86326e85c0082cefb02ec2d4)
a new pair of entries to the configuration:

```diff
--- a/config.gateway.json
+++ b/config.gateway.json
@@ -23,6 +23,13 @@
         ],
         "description": "Access to LTE modem",
         "link": "eth2"
+      },
+       "peth1": {
+        "address": [
+          "192.168.100.2/24"
+        ],
+        "description": "Access to cable modem",
+        "link": "eth0"
       }
     }
   },
@@ -36,6 +43,14 @@
           },
           "outbound-interface": "peth0",
           "type": "masquerade"
+        },
+        "5001": {
+          "description": "Access to cable modem",
+          "destination": {
+            "address": "192.168.100.1"
+          },
+          "outbound-interface": "peth1",
+          "type": "masquerade"
         }
       }
     },
```

Unfortunately, this didn't work, and when I tried to navigate to the cable
modem's `192.168.100.1` address, the connection just timed out. Oddly enough, I
could ping it successfully, but I was stumped as to what was going wrong, and I
didn't touch it for about a month.

Yesterday, though, I needed to access the modem's page, and I remembered that
this had never worked, so I committed myself to fixing it. I had no clue what
was going wrong, so first I needed to understand the problem, and when I'm
looking for insight into network behavior, I usually turn to Wireshark.

Step one was simply to capture the traffic in question. Thankfully this wasn't
too difficult, since I have SSH and root access to the USG:

```text
$ ssh usg.local sudo tcpdump -npi eth0 -w - | ./Wireshark -k -i -
```

With that, I had a Wireshark instance running showing live traffic on the USG's
WAN1 port. Here's a cleaned-up version of what I saw:

{{< figure
src="failing-capture.png"
link="failing-capture.png"
caption="You can see the capture for yourself [here](failing-capture.pcapng)."
alt=`Screenshot of Wireshark showing six packets.
Packet 1: TCP SYN from 192.168.100.2 to 192.168.100.2
Packet 2: ARP broadcast from aa:9f:ec:3e:e8:f3 asking who has 192.168.0.2 to tell 192.168.0.1
Packets 3 and 4 are similar, with packet 3 retransmitting packet 1, and packet 4 retransmitting the ARP request.
Packets 5 and 6 are similar, with packet 5 retransmitting packet 1, and packet 6 retransmitting the ARP request.
` >}}

Right away it was clear something was wrong. Just examining packets 1, 3, and 5,
I could see that while my router's WAN1 port was correctly forwarding traffic
masquerading as the pseudo-ethernet port's address, packets 3 and 5 were TCP
retransmissions — my laptop was retransmitting packets after receiving no
response for a second. Packets 2, 4, and 6 made it clear what was going on. In
each of those packets, the modem broadcasted an ARP request, asking the owner of
`192.168.100.2` to identify itself. Because my router didn't respond, the modem
didn't know how to reply to the TCP packets coming in from `192.168.100.2`, and
it dropped them.

But why wasn't my router replying to ARP requests? I wondered briefly if it
might be some vagary of the pseudo-ethernet configuration, but after taking
another look at the packet capture, I saw the problem: the modem was asking the
owner of `192.168.100.2` to reply to it _at `192.168.0.1`!_ Not only is that
address different from the address the router was trying to use to communicate
with the modem, it's in fact in a totally different subnet, namely
`192.168.0.0/24` rather than `192.168.100.0/24`. As a result, when my router
received the ARP broadcast request, it didn't reply, since the requester was out
of its subnet. As to why the modem does this, I can't say. It seems like an
oversight or error, but maybe there's some deeper logic to it.

Regardless, knowing this made it clear what had to be done: I had to add the
WAN1 pseudo-ethernet interface to the `192.168.0.0/24` subnet, too so that my
router would reply to those unusual ARP requests. Thankfully that subnet doesn't
intersect with any of my network's real subnets, so it was simply a matter of
[adding it to the interface
declaration](https://github.com/ravron/unifi/commit/4b5b30002bd6cd456239ca14b60cf2dea1b31a34):

```diff
--- a/config.gateway.json
+++ b/config.gateway.json
@@ -26,7 +26,8 @@
       },
        "peth1": {
         "address": [
-          "192.168.100.2/24"
+          "192.168.100.2/24",
+          "192.168.0.2/24"
         ],
         "description": "Access to cable modem",
         "link": "eth0"
```

After applying the configuration and reprovisioning the router, communication
with the cable modem from behind my router using its hard-coded `192.168.100.1`
address worked flawlessly.
