"""Domain Search CLI - find available domain names across all TLDs."""

from domain_search.tld_list import fetch_tld_list


def main() -> None:
    tlds = fetch_tld_list()
    print(f"Loaded {len(tlds):,} TLDs from IANA")


if __name__ == "__main__":
    main()
