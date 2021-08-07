+++
title = "Let's Encrypt TLS certificates with UniFi OS"
date =  2021-08-06
categories = ["networking", "unifi"]
summary = """
Always nice when something gets easier."""
+++

Back in 2020, I wrote [a post about using Let's Encrypt TLS certs with a UniFi
Cloud Key]({{< ref "lets-encrypt-unifi-cloud-key" >}}). Since then, Ubiquiti
released an overhaul of their Cloud Key software, dubbed "UniFi OS," which broke
my painstaking TLS setup. In May 2021 I finally decided to investigate, not
without some trepidation. Thankfully, the fixes required were relatively minor,
and TLS is working again. As a bonus, it applies to all of the "apps" that the
new controller software runs, such as UniFi Protect, without additional work.
Before reading this post, you may wish to go review the previous one, linked
above.

The main challenge in getting TLS working on the new system was figuring out
where the certificate and private key needed to be so that the HTTP server would
pick them up and use them. After I SSH'd into the device, a little poking showed
that the new location was `/data/unifi-core/config`, so I made that change
throughout the `remote-uck-setup.bash` script.

I was also thrilled to see that Ubiquiti has done away with the obscure Java
keystore format, and opted for the familiar `.crt` and `.key` DER files. That
let me eliminate a bunch of script used to manipulate the keystore.

You can see the entirety of the modest changes I made in [commit
`7a5df5`](https://github.com/ravron/unifi/commit/7a5df529f88f36a1bf4cc1d8a06bab15bc118acd#).
The [`cert`](https://github.com/ravron/unifi/tree/master/cert) subdirectory of
that repo should now be back in working order. In case you need to access the
old version, it's preserved for posterity at the [`before-unifi-os`
tag](https://github.com/ravron/unifi/tree/before-unifi-os/cert).

Happy encrypting!
