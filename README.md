# acme-tiny-dns-persistent-ovh

OVH DNS record updater for use with [acme-tiny-dns-persistent](https://github.com/nipil/acme-tiny-dns-persistent.git)

This program does the following things

- reads and uses the provided OVH credentials (environment variables)
- reads input in JSONline format (one DNS record per line)
- creates the defined DNS record from json document in your OVH DNS zone
