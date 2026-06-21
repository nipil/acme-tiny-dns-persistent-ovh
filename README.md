# acme-tiny-dns-persistent-ovh

OVH DNS record updater for use with
[acme-tiny-dns-persistent](https://github.com/nipil/acme-tiny-dns-persistent.git)

This program does the following things

- reads and uses the provided OVH credentials (environment variables)
- reads input in JSONline format (one DNS record per line)
- creates the defined DNS record from json document in your OVH DNS zone

## Usage

Reads from STDIN only.

TTL defaults to 60 seconds, so that you can correct challenges
without waiting for hours. This is a rarely queried record anyway !

```text
usage: acme-tiny-dns-persistent-ovh.py [-h] [--log-level {debug,info,warning,error,critical}] [--ttl TTL]

options:
  -h, --help            show this help message and exit
  --log-level {debug,info,warning,error,critical}
  --ttl TTL             Record TTL in seconds
```

## Combined usage

This tools is made to work together with
[acme-tiny-dns-persistent](https://github.com/nipil/acme-tiny-dns-persistent.git)
:

- where `acme_tiny_dns_persistent.py authorize`
  - manages ACME account and configuration
  - produces record specification on STDOUT
  - waits for the actual presence of DNS records to continue
- and `acme-tiny-dns-persistent-ovh.py`
  - reads record specifications on STDIN (from the upstream tool)
  - uses environment variables to build an OVH client
  - uses OVH API to create/update DNS record as needed

```shell
#!/usr/bin/env bash

set -u -e -o pipefail

OVH_ENDPOINT='ovh-eu'
OVH_APPLICATION_KEY='yyy'
OVH_APPLICATION_SECRET='zzz'
OVH_CONSUMER_KEY='xxx'

DOMAIN=test.example.com

# of course you can provide multiple domains !
python3 acme_tiny_dns_persistent.py authorize "$DOMAIN" \
  | python3 acme-tiny-dns-persistent-ovh.py
```

Sample output, with both tools logging level set to `info` :

```text
# comments were added manually to explain what happens in this sample

# acme_tiny_dns_persistent.py starts

INFO Got account https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789 with status `valid`
INFO Got order https://acme-staging-v02.api.letsencrypt.org/acme/order/123456789/41956757994 with status `pending`
INFO Got authz https://acme-staging-v02.api.letsencrypt.org/acme/authz/123456789/2221191274 for `test.example.com` with status `pending`

# acme_tiny_dns_persistent.py prints record specification on STDOUT

INFO Polling for TXT record `_validation-persist.test.example.com` every 3 seconds ...

# acme_tiny_dns_persistent.py waits

# acme_tiny_dns_persistent-ovh.py reads specification from STDIN

INFO Processing {'dns': '_validation-persist.test.example.com', 'type': 'TXT', 'value': 'letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789'} ...
INFO Creating record for {'dns': '_validation-persist.test.example.com', 'type': 'TXT', 'value': 'letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789'}
INFO Refreshing zone: example.com

# acme_tiny_dns_persistent-ovh.py blocks on STDIN, waiting for next record specification

# acme_tiny_dns_persistent.py detects the presence of the actual record in the DNS zone, and completes authorization

INFO Found TXT record `_validation-persist.test.example.com` (only presence is verified)
INFO Polling challenge https://acme-staging-v02.api.letsencrypt.org/acme/chall/123456789/2221191274/aKtryQ for `test.example.com` every 3 seconds (current status `pending`)  ...
INFO Challenge https://acme-staging-v02.api.letsencrypt.org/acme/chall/123456789/2221191274/aKtryQ reached status `valid`
INFO Polling order https://acme-staging-v02.api.letsencrypt.org/acme/order/123456789/41956757994 every 3 seconds (current status `pending`)  ...
INFO Order https://acme-staging-v02.api.letsencrypt.org/acme/order/123456789/41956757994 reached status `ready`

# and so on if multiple records were provided to acme_tiny_dns_persistent.py, then both exit.
```
