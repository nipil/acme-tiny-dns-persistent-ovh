#!/usr/bin/env python3

"""
INPUT SAMPLE

{"dns": "_validation-persist.a.example.com", "type": "TXT", "value": "letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789"}
{"dns": "_validation-persist.b.example.com", "type": "TXT", "value": "letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789; policy=wildcard"}
{"dns": "_validation-persist.c.example.com", "type": "TXT", "value": "letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789; policy=wildcard; persistUntil=2500000000"}
{"dns": "_validation-persist.d.example.com", "type": "TXT", "value": "letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789; persistUntil=2500000000"}

OVH DNS API RECORD SAMPLE

record={
    'fieldType': 'TXT',
    'id': 1234567890,
    'subDomain': '_validation-persist.test-staging',
    'target': '"letsencrypt.org; accounturi=https://acme-staging-v02.api.letsencrypt.org/acme/acct/123456789; policy=wildcard; persistUntil=2500000000"',
    'ttl': 3600,
    'zone': 'example.com'
}

ADDITIONAL INFORMATION

OVH does quote the TXT values (wether you wanted them or not) and this seems to be a convention in DNS TXT records or applications.
"""

import json, logging, sys
from argparse import ArgumentParser

from ovh import APIError, Client


class AppError(Exception):
    pass


DNS_RECORD_ZONE_PARTS = 2


def run(ttl: int) -> None:
    try:
        client = Client()
    except APIError as e:
        raise AppError(e)

    # cache of zones and record
    zones = {zone: dict() for zone in client.get("/domain/zone")}
    refresh_zones = set()
    logging.debug(f"OVH known zones: {zones.keys()}")

    # process JSONline input
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        # parse input line and verify its structure
        try:
            spec = json.loads(line)
        except json.JSONDecodeError as e:
            raise AppError(f"Error parsing json `{line}`: {e}")
        if not all(spec.get(key, None) is not None for key in ("dns", "type", "value")):
            raise AppError("Missing or invalid required keys in input JSON")
        logging.info(f"Processing {spec} ...")

        # extract zone and sub-domain from record name
        dns = spec["dns"].split(".")
        if len(dns) < DNS_RECORD_ZONE_PARTS:
            raise AppError(f"Invalid DNS record name: {dns}")
        sub_domain = ".".join(dns[:-DNS_RECORD_ZONE_PARTS])
        zone = ".".join(dns[-DNS_RECORD_ZONE_PARTS:])
        if zone not in zones:
            raise AppError(f"This OVH credential has no access to {zone}.")
        logging.debug(f"Parsed domain: {zone=} {sub_domain=}")

        # cache zone records
        for record_id in client.get(f"/domain/zone/{zone}/record"):
            if record_id not in zones[zone]:
                zones[zone][record_id] = client.get(
                    f"/domain/zone/{zone}/record/{record_id}"
                )

        # look for any record matching our exact spec
        forget_ids = []
        for record_id, record in zones[zone].items():
            # skip non-matching records
            if (
                record["subDomain"] != sub_domain
                or record["fieldType"] != spec["type"].upper()
            ):
                continue
            # compare matching record's parameters
            if record["ttl"] == ttl and record["target"].strip('"') == spec[
                "value"
            ].strip('"'):
                logging.info(f"Found existing record matching {spec}")
                continue

            # update existing if different
            logging.info(f"Updating existing record to match {spec}")
            client.put(
                f"/domain/zone/{zone}/record/{record_id}",
                subDomain=sub_domain,
                target=spec["value"],
                ttl=ttl,
            )

            # mark record cache as invalid, and zone needs refresh
            forget_ids.append(record_id)
            refresh_zones.add(zone)
            break

        else:
            # add missing record if we did not find any
            logging.info(f"Creating record for {spec}")
            client.post(
                f"/domain/zone/{zone}/record",
                fieldType=spec["type"].upper(),
                subDomain=sub_domain,
                target=spec["value"],
                ttl=ttl,
            )
            # zone needs refresh
            refresh_zones.add(zone)

        # clean cache of invalid records
        for forget_id in forget_ids:
            zones[zone].pop(forget_id, None)

    # refresh modified zones
    for refresh_zone in refresh_zones:
        logging.info(f"Refreshing zone: {refresh_zone}")
        client.post(f"/domain/zone/{refresh_zone}/refresh")


def main(argv) -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="warning",
    )
    parser.add_argument("--ttl", type=int, default=60)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s %(message)s",
    )
    logging.debug(f"Arguments: {args}")

    try:
        run(args.ttl)
    except KeyboardInterrupt:
        logging.warning(f"Interrupted by user")
        exit(1)
    except AppError as e:
        logging.critical(f"Fatal: {e}")
        exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
