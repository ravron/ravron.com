+++
title = "Using Let's Encrypt TLS certificates on the UniFi Cloud Key"
date = 2020-09-09
categories = ["networking", "unifi"]
summary = """
How I convinced my browser that my network controller isn't trying to steal my credit card."""
+++

I've been running UniFi equipment at home for over a year, now, and it's
generally been great. The hardware performs splendidly, the network is stable,
and I can indulge my desire to tinker, creating segregated VLANs, setting up an
LTE WAN fallback, etc. However, through all that time, there's been a nagging
annoyance that I've finally gotten around to solving.

I originally hosted the UniFi Network Controller — hereafter just "controller" —
on my Raspberry Pi 3 B, but later bought a [Cloud Key Gen2
Plus](https://unifi-protect.ui.com/cloud-key-gen2) because maintaining the
installation on the Pi was something of a chore, and I wanted to use UniFi
Protect, Ubiquiti's security camera offering. On both devices, though, I noticed
that while the controller was accessed via HTTPS, the TLS certificate it used
was a hard-coded self-signed cert generated by Ubiquiti. My browser was
rightfully spooked, dutifully warning me that my "connection was not private."

{{< figure
src="connection-not-private.png"
alt=`A screenshot of an error page in Brave browser which reads "Your
connection is not private. Attackers might be trying to steal your information
from 192.168.1.3 (for example, passwords, messages, or credit cards)." There is
also a "Learn more" link, and the error identifier
"NET::ERR_CERT_COMMON_NAME_INVALID." Two buttons at the bottom read
"Advanced" and "Back to safety"`
>}}

Though my browser, Brave, caches my bypass of this warning for a little while,
it still eventually returns. The cached "yes I know what I'm doing" response can
also expire while I'm using the controller UI, which results in the confusing
effect of the site's AJAX calls silently failing, so the controller appears to
lock up until I reload and once again reassure the browser all is well.

Of course I am _far_ from the first person to notice this issue:

- [Installing SSL/TLS certs in UniFi controllers](https://binaryfury.wann.net/2016/01/installing-ssltls-certs-in-unifi-controllers/)
- [Installing an SSL certificate on Ubiquiti Unifi](https://www.namecheap.com/support/knowledgebase/article.aspx/10134/33/installing-an-ssl-certificate-on-ubiquiti-unifi)
- [Installing a custom SSL certificate on a UniFi Controller](https://www.cracknells.co.uk/servers-side/installing-a-custom-ssl-certificate-on-a-unifi-controller/)
- [How To Install a Let’s Encrypt SSL Certificate on UniFi](https://crosstalksolutions.com/lets-encrypt-unifi/)
- [Install Letsencrypt SSL Certificate for Unifi Controller on Raspberry Pi](https://lazyadmin.nl/home-network/unifi-controller-ssl-certificate/)

There are many more. They range in age, with some as early as 2015, and
approach, using all manner of certificates, with manual, automated or "sort
of" automated installation. I looked at this situation and decided it was time
to try my hand at it, in part because none of the existing solutions seemed to
satisfy my goals. The ideal setup would:

1. Renew automatically
1. Be low or zero cost
1. Have easy, idempotent setup
1. Require minimal modifications to the Cloud Key
1. Not require exposing the Cloud Key to the internet

With these objectives in mind I set out to build something to suit. While I used
a number of resources working on this, I should give special credit to [this
post by Gerd
Naschenweng](https://www.naschenweng.info/2017/01/06/securing-ubiquiti-unifi-cloud-key-encrypt-automatic-dns-01-challenge/),
which describes an end result fairly similar to what I did here.

## Planning for automatic renewal with ACME v2

[Let's Encrypt](https://letsencrypt.org/) is by now well known. It's a
non-profit certificate authority (CA) which issues free TLS certificates with
short lifetimes, and provides first-class support for renewal automation.
Certificate issuance is handled via the IETF-designed [ACME
protocol](https://en.wikipedia.org/wiki/Automated_Certificate_Management_Environment)
which defines mechanisms for CAs to automatically verify ownership of a domain.
Let's Encrypt [lists a _ton_ of ACME
clients](https://letsencrypt.org/docs/client-options/), and I was certain I
could find one that suited my needs.

After a little poking around, I found that while
[Certbot](https://certbot.eff.org/) is the recommended ACME client, the Python
environment on the Cloud Key isn't great, and the default `apt` source lists
pointed to an old version of Certbot. I could have installed newer Python
versions and added the necessary `apt` sources, but I decided to give
[acme.sh](https://github.com/acmesh-official/acme.sh), an ACME client written
entirely in Bash, a try instead. It's both beautiful and terrible to behold [its
source](https://github.com/acmesh-official/acme.sh/blob/053f4a9a2e7f74aaec4493f5e9828f229088ab7c/acme.sh),
7,454 lines of Bash script as of this writing. As I worked with it, I found its
documentation lacking — I spent no small amount of time reading its source — but
it definitely got the job done.

## Installation

That choice made, I started on the idempotent setup script. First, some sanity
checks to ensure I couldn't do something too foolish.

```bash
set -eux

if [[ $SHELL != '/bin/bash' ]]; then
    echo "wrong shell, expected /bin/bash, got $SHELL"
    exit 1
fi

# Do a lazy check to try to prevent accidentally runs on a non-cloud key device
if ! [[ -d /usr/lib/unifi ]]; then
    echo 'this script should only be run on the cloud key'
    exit 1
fi
```

Next, installing acme.sh. The [README recommends a pipe-to-shell "online"
installation
method](https://github.com/acmesh-official/acme.sh/tree/053f4a9a2e7f74aaec4493f5e9828f229088ab7c#1-install-online),
but it wouldn't allow me to set the flags I wanted, and I'm no fan of piping
source from the internet directly into my shell anyways. The next recommendation
involves cloning the repo, but the Cloud Key doesn't have `git`, and I would
prefer to avoid installing it.

Instead, I ended up downloading a gzipped tarball from GitHub, effectively a
poor man's clone. With `trap`, it's easy to ensure that your temporary working
directory is cleaned up.

```bash
# Subshell to automatically pop cd and rm working dir
(
# Make a working dir
tmpdir=$(mktemp -d)
trap "rm -rf $tmpdir" EXIT
cd $tmpdir

# Get acme.sh
curl --silent \
    --location \
    'https://github.com/acmesh-official/acme.sh/archive/master.tar.gz' | \
    tar -xz

cd acme.sh-master

# Run installer
./acme.sh \
    --debug 3 \
    --install \
    --nocron \
    --noprofile \
    --auto-upgrade
)
```

I didn't need to run acme.sh interactively, nor did I want its auto-generated
cron entry, hence the corresponding flags. After this ran successfully, it
populated `~/.acme.sh/` with a handful of files and directories, including the
script itself at `~/.acme.sh/acme.sh`.

## Configuration

acme.sh, like most ACME clients, accepts hooks which allow you to do things
before or after certs are renewed. The easiest way to implement these hooks is
more shell scripts, so the next thing my setup script does is write those hook
scripts to disk. First is the prehook file:

```bash
# Create the prehook file
cat <<'EOF' >~/.acme.sh/prehook.bash
#!/bin/bash

set -eux

mkdir -p ~/.acme.sh/backups
cd ~/.acme.sh/backups

tar -zcvf ~/.acme.sh/backups/tls-backup-$(date --iso-8601=seconds).tgz /etc/ssl/private/*
EOF
```

The prehook script runs before every attempt to renew a certificate. In this
case, it zips up all the current TLS secrets and dumps them into a backup
directory inside `~/.acme.sh`. In case something goes catastrophically wrong, it
means I at least have something to manually restore.

Next is the reload hook.

```bash
# Create the reload file
cat <<'EOF' >~/.acme.sh/reload.bash
#!/bin/bash

set -eux

cd /etc/ssl/private

(
trap 'rm -f /etc/ssl/private/cloudkey.p12' EXIT

CERT_PFX_PATH=/etc/ssl/private/cloudkey.p12 ~/.acme.sh/acme.sh \
    --to-pkcs12 \
    --domain unifi.ravron.com \
    --password aircontrolenterprise

# keytool's src alias is the name of the entry, or just its index, starting at
# 1, if not present. acme.sh's --to-pkcs12 doesn't know how to set the name, so
# we have to use the index instead.
keytool -importkeystore \
    -deststorepass aircontrolenterprise \
    -destkeypass aircontrolenterprise \
    -destkeystore unifi.keystore.jks \
    -srckeystore cloudkey.p12 \
    -srcstoretype PKCS12 \
    -srcstorepass aircontrolenterprise \
    -srcalias 1 \
    -destalias unifi \
    -noprompt
)

md5sum unifi.keystore.jks > unifi.keystore.jks.md5

chown root:ssl-cert cloudkey.crt cloudkey.key unifi.keystore.jks.md5
chown unifi:ssl-cert unifi.keystore.jks

chmod 640 cloudkey.crt cloudkey.key unifi.keystore.jks unifi.keystore.jks.md5

# Test nginx config, then reload
/usr/sbin/nginx -t
service nginx reload

# unifi and unifi-protect don't obey reload, so we have to restart them
# entirely. Surprise, surprise.
service unifi restart

# If this system has unifi-protect, restart it too
systemctl is-active --quiet unifi-protect.service && service unifi-protect restart

# If there are more than five backups, delete all but the most recent 5. Do this
# in the reload hook so that we don't delete backups on failed renewals.
rm -f $(ls -1 tls-backup-*.tgz | head -n -5)
EOF
```

This one's a lot more complicated. The reload hook runs after all certs have
been renewed, if the renewal was successful. It's intended to restart the
services that need to pick up the new configuration. In this case, it also does
a bit of custom key munging to get the new certificate chain and private key
into the Java keystore format that the controller, and UniFi Protect, need. It's
similar to many other scripts intended to update the controller's keystore, but
it also is careful to fix permissions, update the checksum file, and restart the
relevant services as efficiently as possible. The final command cleans up all
but the most recent five backup files. I do this here, rather than in the
prehook, to ensure that no backups are removed until the renewal has finished
successfully.

## Issuing the certificate

Version 2 of the ACME protocol offers [three different challenge
types](https://letsencrypt.org/docs/challenge-types/). The third, TLS-ALPN-01,
is for pretty niche uses, and not appropriate here. In short, here's how the
other two work:

- HTTP-01: the CA gives the client a nonce to put on the webserver that the
  domain being validated points to, and the CA then fetches the nonce and
  confirms it is correct.
- DNS-01: the CA gives the client a nonce to put in a TXT DNS record, and the CA
  then runs a DNS lookup and confirms it is correct

You'll note that HTTP-01 requires that the client requesting the certificate be
accessible from the internet so that the CA's infrastructure can make an HTTP
request to it. This is exactly what I was trying to avoid, so I ruled out
HTTP-01 and turned to DNS-01.

acme.sh supports DNS-01 via whole bunch of shell script "modules" in its [dnsapi
subdirectory](https://github.com/acmesh-official/acme.sh/tree/053f4a9a2e7f74aaec4493f5e9828f229088ab7c/dnsapi).
After Let's Encrypt provides the challenge nonce that should be put into a TXT
record on the domain being validated, acme.sh uses the selected module to
interact with the DNS provider's API and add the record. My domain's DNS
provider is [Route53](https://aws.amazon.com/route53/), and acme.sh has [a
module to support
it](https://github.com/acmesh-official/acme.sh/blob/053f4a9a2e7f74aaec4493f5e9828f229088ab7c/dnsapi/dns_aws.sh).
However, there is of course a catch: editing Route53 records means that I have
to provide access to my AWS account so that acme.sh can add a TXT record to the
unifi.ravron.com subdomain.

As usual, I want to ensure that any authorization I issue is as limited as
reasonably possible. There's a [short wiki
page](https://github.com/acmesh-official/acme.sh/wiki/How-to-use-Amazon-Route53-API)
that describes how to set up the necessary IAM permissions for acme.sh, and I
largely followed it, using the appendix's "more restrictive" policy. However, I
was a little nervous giving my cloud key access to do effectively anything with
the ravron.com domain, and I did look for a way to scope down those permissions.
I found [this excellent analysis of schemes to reduce authorization
scope](https://www.eff.org/deeplinks/2018/02/technical-deep-dive-securing-automation-acme-dns-challenge-validation)
from the EFF, and I decided to implement one of its suggested mitigations: I
created a new hosted zone in Route53 and delegated authority for
unifi.ravron.com from the ravron.com hosted zone to the new hosted zone,
following [the
documentation](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-routing-traffic-for-subdomains.html#dns-routing-traffic-for-subdomains-new-hosted-zone).
Then, I restricted the IAM policy to acting only on that hosted zone, so that
the worst an attacker could do if they stole the new AWS account credentials
would be mess with the DNS records for unifi.ravron.com. While that wouldn't be
great, it's much better than exposing ravron.com.

With the new IAM user's access keys in hand, I needed to pass them securely to
acme.sh. acme.sh stores the IAM credentials in its configuration files after
first use, but to get them initially, it reads them out of the standard
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables. So,
simply export those, being careful to disable xtrace logging:

```bash
set +x
export AWS_ACCESS_KEY_ID="$1"
export AWS_SECRET_ACCESS_KEY="$2"
set -x
```

(I'll explain how the credentials get into `$1` and `$2` a little later)

Finally, we're ready to issue a certificate.

```bash
# Issue a cert. This won't actually do anything if the cert does not need
# renewal. It will always update the configuration, saving hooks, AWS creds,
# output filepaths, etc. Note there strict rate limits on production cert
# generation. When testing this script, add `--staging` to the command below.
# Let's Encrypt's staging servers will be used indefinitely until you remove the
# `--staging` option and re-run the setup script.
~/.acme.sh/acme.sh \
    --staging \
    --issue \
    --dns dns_aws \
    --domain unifi.ravron.com \
    --pre-hook ~/.acme.sh/prehook.bash \
    --reloadcmd ~/.acme.sh/reload.bash \
    --fullchain-file /etc/ssl/private/cloudkey.crt \
    --key-file /etc/ssl/private/cloudkey.key \
    --accountemail 'ravron@posteo.net' || true
```

The command is largely self-explanatory. Note though that as written it
communicates with Let's Encrypt's staging environment, so the certificate issued
won't be accepted by browsers. I've done this here because the production
environment has somewhat stringent [rate
limits](https://letsencrypt.org/docs/rate-limits/) to prevent abuse, while the
staging environment's rate limits are [dramatically
looser](https://letsencrypt.org/docs/staging-environment/). Once you've tested
the script and got it configured, you should remove the `--staging` flag and
re-run the setup to ensure that future renewals will use the production
environment.

The command takes a little while, because it must communicate with Let's
Encrypt, then modify my DNS records and sleep a while before asking Let's
Encrypt to check them. Eventually, it generates a certificate and runs the
reload hook to put it into the Java keystore and restart the various services on
the Cloud Key.

## Automating renewal

The final step is to automate renewal using systemd. acme.sh can automatically
generate a cron file, but I prefer systemd for its flexibility and because it's
what I use on my other machines. There's a [helpful wiki
page](https://github.com/acmesh-official/acme.sh/wiki/Using-systemd-units-instead-of-cron)
on the topic, at least, and I largely followed its advice.

```bash
cat <<'EOF' >/etc/systemd/system/acme.service
[Unit]
Description=Renew Let's Encrypt certificates using acme.sh
After=network-online.target

[Service]
Type=oneshot
ExecStart=/root/.acme.sh/acme.sh --cron --home /root/.acme.sh
# acme.sh returns 2 when renewal is skipped (i.e. certs up to date)
SuccessExitStatus=0 2
EOF

# Stop and disable any existing timer
systemctl disable --now acme.timer || true

cat <<'EOF' >/etc/systemd/system/acme.timer
[Unit]
Description=Daily renewal of Let's Encrypt's certificates

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now acme.timer
```

Here I write out the [service
file](https://www.freedesktop.org/software/systemd/man/systemd.service.html),
then the [timer
file](https://www.freedesktop.org/software/systemd/man/systemd.timer.html). The
timer will run daily, with a one-hour randomized delay, and invoke the oneshot
service. The service in turn calls `acme.sh --cron`, which checks each issued
certificate to see if it's approaching its not-valid-after date, and renews it
if so. All of the hooks and filepaths used during the original `--issue` command
are saved and re-used, so there's no need to specify them again here.

It's now easy to check when the next renewal check will happen using `systemctl
status`:

```
$ systemctl status acme.timer
● acme.timer - Daily renewal of Let's Encrypt's certificates
   Loaded: loaded (/etc/systemd/system/acme.timer; enabled; vendor preset: enabled)
   Active: active (waiting) since Wed 2020-09-09 19:42:59 PDT; 39min ago
  Trigger: Thu 2020-09-10 00:40:58 PDT; 4h 18min left
```

And, as with any systemd unit, it's also easy to check the logs with
`journalctl -u acme.service`.

## Finishing touches

There's still a couple things left to be sorted out. First, how does this script
get run on the Cloud Key? And second, more importantly, how do the AWS
credentials get into the positional parameters I mentioned earlier?

The answer is simple, if unexciting: a wrapper script grabs the keys using the
`aws` tool, then invokes the main setup script remotely via SSH.

```zsh
set -eu

KEY_ID=$(aws configure get profile.acme.aws_access_key_id)
SECRET_KEY=$(aws configure get profile.acme.aws_secret_access_key)

ssh uck 'bash -s' < remote-uck-setup.bash "$KEY_ID" "$SECRET_KEY"
```

You can find both [the main
script](https://github.com/ravron/unifi/blob/74d8958e924a028b26fbc8286f0782aa29ca66f7/cert/remote-uck-setup.bash)
I've discussed and [the
wrapper](https://github.com/ravron/unifi/blob/74d8958e924a028b26fbc8286f0782aa29ca66f7/cert/uck-setup.zsh)
on [GitHub](https://github.com/ravron/unifi/tree/74d8958e924a028b26fbc8286f0782aa29ca66f7/cert).

## Issues I encountered

I ran into a few issues while setting all this up, and I want to cover them
briefly here so that you might avoid what I did not.

First was rate limiting. I didn't realize how strict the rate limits set on the
Let's Encrypt production environment were until I ran into them. The one that'll
get you is the limit of five renewals per unique set of domain names per _week_.
Once I ran into this, I was forced to use the staging certs until a week had
elapsed. Don't make this mistake, it's annoying — test with staging until you've
got everything working perfectly.

Second was [HTTP Strict Transport
Security](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html),
or HSTS. ravron.com includes the strict-transport-security header:

```
$ curl -sI https://ravron.com | grep strict
strict-transport-security: max-age=63072000; includeSubDomains; preload
```

which tells the browser that this domain and all its subdomains must not be
loaded insecurely. This became a problem after I ran into the rate limiting
issue I described earlier, because once I started using a staging certificate,
my browser wouldn't let me load unifi.ravron.com, no matter how I insisted. Of
course, I could still access it via its LAN IP addresses, and once I got a
production certificate installed again, all was well. I simply found it amusing
that the HSTS I intended for use on this site was also (correctly, if
confusingly) being applied to this internal-only domain.

Finally, less an issue than a last step, I did have to set up a static DNS entry
on my network's DNS server such that unifi.ravron.com resolved to my
controller's IP.

If you run into any issues, or find this guide lacking, send me an email, and
I'll update the page to be more helpful.

## Resources

I picked pieces from a wide variety of resources while getting this working.
Here's a rather disorganized list so you can do your own research.

- [EFF's Certbot guide](https://certbot.eff.org/docs/using.html)
- [Adding Let's Encrypt certificate to UniFi Cloud Key without exposing UniFi to
  the
  internet](https://community.ui.com/stories/Adding-Lets-Encrypt-certificate-to-UniFi-Cloud-Key-without-exposing-UniFi-to-the-internet/709219e3-32ee-41a8-a0a3-746e8a67e27e)
  on the Ubiquiti forums
- [Use already existing SSL for unifi
  controller](https://community.ui.com/questions/Use-already-existing-SSL-for-unifi-controller/f4472600-7d69-461b-9cc3-46cde7f1ce15)
  on the Ubiquiti forums
- [`keytool`
  reference](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/keytool.html)
- [Let's Encrypt documentation](https://letsencrypt.org/docs/)
- [Gerd Naschenweng's Securing Ubiquiti UniFi Cloud Key with Let’s Encrypt SSL
  and automatic dns-01
  challenge](https://www.naschenweng.info/2017/01/06/securing-ubiquiti-unifi-cloud-key-encrypt-automatic-dns-01-challenge/)