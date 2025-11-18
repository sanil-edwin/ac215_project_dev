IOWA_FIPS_PREFIX = "19"

def is_iowa_fips(fips: str) -> bool:
    return isinstance(fips, str) and fips.strip().zfill(5).startswith(IOWA_FIPS_PREFIX)

def ensure_iowa_fips_list(fips_list):
    bad = [f for f in fips_list if not is_iowa_fips(f)]
    return bad
