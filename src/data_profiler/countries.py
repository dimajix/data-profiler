"""Countries: the codes of two and three letters, numbers and English names of those of ISO 3166.

The countries are those of ISO 3166-1 today, as `pycountry` holds them, and all those withdrawn from
it, of ISO 3166-3, which `pycountry` holds as well, as an older database may well hold `DDR`, `SUN`
or `YUG`. A code of a country withdrawn may be one of a country today as well: `BY`, `SK`, `ATF`.

A country is written by its name of ISO 3166 - `Germany`, `Korea, Republic of` -, by its official
name - `Federal Republic of Germany` -, by its common name - `South Korea` -, where ISO 3166 gives
them, or by a name more common, which ISO 3166 does not give - `USA`, `Russia`, `Soviet Union`. No
name is left out as a word of other columns, as the names of currencies are: no column holds
`Chad`, `Jordan` or `Georgia` in half of its values.
"""

from typing import Final

from pycountry import countries, historic_countries

# Names of countries more common than those of ISO 3166: short forms and older names of countries of
# today and of those withdrawn, and the names of ISO 3166 of letters with accents written without.
_COMMON: Final = (
    "Aland Islands",
    "Britain",
    "Brunei",
    "Burma",
    "Byelorussia",
    "Cape Verde",
    "Cote d'Ivoire",
    "Curacao",
    "Czechoslovakia",
    "Democratic Republic of the Congo",
    "DR Congo",
    "East Germany",
    "Falkland Islands",
    "GDR",
    "Great Britain",
    "Holland",
    "Holy See",
    "Ivory Coast",
    "Macau",
    "Macedonia",
    "Micronesia",
    "North Vietnam",
    "Palestine",
    "Pitcairn Islands",
    "Republic of Korea",
    "Reunion",
    "Rhodesia",
    "Russia",
    "Saint Barthelemy",
    "Saint Martin",
    "Sint Maarten",
    "South Yemen",
    "Soviet Union",
    "Swaziland",
    "The Bahamas",
    "The Gambia",
    "The Netherlands",
    "Turkey",
    "Turkiye",
    "U.K.",
    "U.S.",
    "U.S. Virgin Islands",
    "U.S.A.",
    "UAE",
    "UK",
    "Upper Volta",
    "US Virgin Islands",
    "USA",
    "USSR",
    "Vatican",
    "Vatican City",
    "West Germany",
    "Yugoslavia",
    "Zaire",
)

# Each country, of today or withdrawn, as `pycountry` holds it, whose fields are typed as of any
# type, so that the tuples below say they are of texts.
_COUNTRIES: Final = (*countries, *historic_countries)

ALPHA_2: Final[tuple[str, ...]] = tuple(sorted({country.alpha_2 for country in _COUNTRIES}))
"""The codes of two letters of the countries, in capitals, `DE`, sorted."""

ALPHA_3: Final[tuple[str, ...]] = tuple(sorted({country.alpha_3 for country in _COUNTRIES}))
"""The codes of three letters of the countries, in capitals, `DEU`, sorted."""

NUMBERS: Final[tuple[str, ...]] = tuple(
    sorted({country.numeric for country in _COUNTRIES if hasattr(country, "numeric")})
)
"""The numbers of the countries, of three digits, `276`, sorted."""

NAMES: Final[tuple[str, ...]] = tuple(
    sorted(
        {
            getattr(country, kind)
            for country in _COUNTRIES
            for kind in ("name", "official_name", "common_name")
            if hasattr(country, kind)
        }
        | set(_COMMON)
    )
)
"""The English names of the countries, of ISO 3166 and more common ones, `Germany`, sorted."""
