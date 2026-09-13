import pandas as pd

from hdb_etl.config import RESALE_IDENTIFIER_COL
from hdb_etl.transform import (
    add_resale_identifier,
    block_digits,
    build_resale_identifier,
    first_two_digits_of_amount,
    format_remaining_lease,
    remaining_lease_parts,
    sha256_hex,
)


def test_block_digits_padding_and_letters():
    assert block_digits("19") == "019"
    assert block_digits("6A") == "006"
    assert block_digits("309A") == "309"
    assert block_digits("1234") == "123"


def test_average_price_first_two_digits():
    assert first_two_digits_of_amount(230000) == "23"
    assert first_two_digits_of_amount(95000) == "95"
    assert first_two_digits_of_amount(1_200_000) == "12"
    assert first_two_digits_of_amount(9) == "09"


def test_resale_identifier_example():
    # S + 019 + 23 + 01 + A
    assert build_resale_identifier("19", 230000, "2012-01", "ANG MO KIO") == "S0192301A"


def test_remaining_lease_matches_known_source_year():
    years, months = remaining_lease_parts(1986, "2015-01")
    assert (years, months) == (70, 0)
    years, months = remaining_lease_parts(1986, "2015-06")
    assert (years, months) == (69, 7)
    assert format_remaining_lease(61, 4) == "61 years 04 months"
    assert format_remaining_lease(62, 1) == "62 years 01 month"


def test_column_name_matches_brief():
    frame = pd.DataFrame(
        [
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "2 ROOM",
                "block": "19",
                "resale_price": 230000,
            }
        ]
    )
    out = add_resale_identifier(frame)
    assert RESALE_IDENTIFIER_COL in out.columns
    assert out[RESALE_IDENTIFIER_COL].iloc[0] == "S0192301A"


def test_sha256_is_stable_and_64_hex():
    digest = sha256_hex("S0192301A")
    assert len(digest) == 64
    assert digest == sha256_hex("S0192301A")
    assert digest != sha256_hex("S0192301B")
