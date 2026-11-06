"""Currencies: the alphabetic codes, numbers and English names of the currencies of ISO 4217.

The currencies are those of ISO 4217 today, as `pycountry` holds them, and those withdrawn from it
since the euro, 1999, of its list of withdrawn currencies as published on 2026-01-01, which
`pycountry` does not hold, as an older database may well hold `DEM` or `FRF`. Left out are `XTS`,
the code of testing, and `XXX`, of no currency, which stands for an unknown value in many a column.

A currency is written by its name of ISO 4217 - `Pound Sterling`, `Lek` - or by a name more common,
which ISO 4217 does not give - `British Pound`, `Albanian Lek`. The names that are words of other
columns as well are left out - `Gold`, a tier of customers, `Won`, a stage of a sale, `Pound`, a
unit of weight -, as a column of them is more often of another kind than of currencies; their codes
are not, nor the names more common that hold them, `Japanese Yen`.
"""

from typing import Final

from pycountry import currencies

# The codes of ISO 4217 of no currency.
_NONE: Final = frozenset({"XTS", "XXX"})

# The names of ISO 4217 that are words of other columns as well: of the precious metals, of the
# tiers of customers, and of a few currencies, `Won`, a stage of a sale, `Sol`, `Rand`, `Yen`,
# `Sucre`.
_WORDS: Final = frozenset(
    {"Gold", "Silver", "Platinum", "Palladium", "Won", "Sol", "Rand", "Yen", "Sucre"}
)

# The currencies withdrawn from ISO 4217 since 1999 whose codes are no longer current: each code,
# its number, None where it has none, and its name, of each name the code had once.
_WITHDRAWN: Final = (
    ("ADP", "020", "Andorran Peseta"),
    ("AFA", "004", "Afghani"),
    ("ANG", "532", "Netherlands Antillean Guilder"),
    ("AON", "024", "New Kwanza"),
    ("AOR", "982", "Kwanza Reajustado"),
    ("ATS", "040", "Schilling"),
    ("AYM", "945", "Azerbaijan Manat"),
    ("AZM", "031", "Azerbaijanian Manat"),
    ("BEF", "056", "Belgian Franc"),
    ("BGL", "100", "Lev"),
    ("BGN", "975", "Bulgarian Lev"),
    ("BYB", "112", "Belarusian Ruble"),
    ("BYR", "974", "Belarusian Ruble"),
    ("CHC", "948", "WIR Franc (for electronic)"),
    ("CSD", "891", "Serbian Dinar"),
    ("CUC", "931", "Peso Convertible"),
    ("CYP", "196", "Cyprus Pound"),
    ("DEM", "276", "Deutsche Mark"),
    ("ECS", "218", "Sucre"),
    ("ECV", "983", "Unidad de Valor Constante (UVC)"),
    ("EEK", "233", "Kroon"),
    ("ESP", "724", "Spanish Peseta"),
    ("FIM", "246", "Markka"),
    ("FRF", "250", "French Franc"),
    ("GHC", "288", "Cedi"),
    ("GHP", "939", "Ghana Cedi"),
    ("GRD", "300", "Drachma"),
    ("HRK", "191", "Croatian Kuna"),
    ("HRK", "191", "Kuna"),
    ("IEP", "372", "Irish Pound"),
    ("ITL", "380", "Italian Lira"),
    ("LTL", "440", "Lithuanian Litas"),
    ("LUF", "442", "Luxembourg Franc"),
    ("LVL", "428", "Latvian Lats"),
    ("MGF", "450", "Malagasy Franc"),
    ("MRO", "478", "Ouguiya"),
    ("MTL", "470", "Maltese Lira"),
    ("MZM", "508", "Mozambique Metical"),
    ("NLG", "528", "Netherlands Guilder"),
    ("PTE", "620", "Portuguese Escudo"),
    ("ROL", "642", "Old Leu"),
    ("RUR", "810", "Russian Ruble"),
    ("SDD", "736", "Sudanese Dinar"),
    ("SIT", "705", "Tolar"),
    ("SKK", "703", "Slovak Koruna"),
    ("SLL", "694", "Leone"),
    ("SRG", "740", "Surinam Guilder"),
    ("STD", "678", "Dobra"),
    ("TJR", "762", "Tajik Ruble"),
    ("TMM", "795", "Turkmenistan Manat"),
    ("TPE", "626", "Timor Escudo"),
    ("TRL", "792", "Old Turkish Lira"),
    ("USS", "998", "US Dollar (Same day)"),
    ("VEB", "862", "Bolivar"),
    ("VEF", "937", "Bolivar"),
    ("VEF", "937", "Bolivar Fuerte"),
    ("VEF", "937", "Bolívar"),
    ("XEU", "954", "European Currency Unit (E.C.U)"),
    ("XFO", None, "Gold-Franc"),
    ("XFU", None, "UIC-Franc"),
    ("XRE", None, "RINET Funds Code"),
    ("YUM", "891", "New Dinar"),
    ("ZMK", "894", "Zambian Kwacha"),
    ("ZRN", "180", "New Zaire"),
    ("ZWD", "716", "Zimbabwe Dollar"),
    ("ZWD", "716", "Zimbabwe Dollar (old)"),
    ("ZWL", "932", "Zimbabwe Dollar"),
    ("ZWN", "942", "Zimbabwe Dollar (new)"),
    ("ZWR", "935", "Zimbabwe Dollar"),
)

# Names of currencies more common than those of ISO 4217: of the currencies most traded, their
# short forms among them - `Yuan`, `D-Mark` -, of those whose names of ISO 4217 do not name
# their countries, and the names of ISO 4217 of a typographic apostrophe with a straight one.
_COMMON: Final = (
    "Afghan Afghani",
    "Albanian Lek",
    "American Dollar",
    "Angolan Kwanza",
    "Austrian Schilling",
    "Bangladeshi Taka",
    "Belarusian Rouble",
    "Bhutanese Ngultrum",
    "Bolivian Boliviano",
    "Bosnia and Herzegovina Convertible Mark",
    "Botswana Pula",
    "British Pound",
    "British Pound Sterling",
    "Cambodian Riel",
    "Central African CFA Franc",
    "Chinese Renminbi",
    "Chinese Yuan",
    "Costa Rican Colón",
    "Czech Crown",
    "Danish Crown",
    "D-Mark",
    "Dutch Guilder",
    "Emirati Dirham",
    "Eritrean Nakfa",
    "Estonian Kroon",
    "Finnish Markka",
    "Gambian Dalasi",
    "Georgian Lari",
    "German Mark",
    "Greek Drachma",
    "Guatemalan Quetzal",
    "Haitian Gourde",
    "Honduran Lempira",
    "Hungarian Forint",
    "Icelandic Krona",
    "Indonesian Rupiah",
    "Israeli New Shekel",
    "Israeli Shekel",
    "Japanese Yen",
    "Kazakhstani Tenge",
    "Korean Won",
    "Kyrgyzstani Som",
    "Lesotho Loti",
    "Macanese Pataca",
    "Macedonian Denar",
    "Maldivian Rufiyaa",
    "Mauritanian Ouguiya",
    "Mongolian Tugrik",
    "Myanmar Kyat",
    "Nicaraguan Cordoba",
    "Nigerian Naira",
    "Norwegian Crown",
    "Omani Rial",
    "Pa'anga",
    "Panamanian Balboa",
    "Papua New Guinean Kina",
    "Paraguayan Guarani",
    "Peruvian Sol",
    "Polish Zloty",
    "Renminbi",
    "Russian Rouble",
    "Samoan Tala",
    "Sao Tome and Principe Dobra",
    "Sierra Leonean Leone",
    "Slovenian Tolar",
    "South African Rand",
    "South Korean Won",
    "Swazi Lilangeni",
    "Swedish Crown",
    "Taiwan Dollar",
    "Tajikistani Somoni",
    "Thai Baht",
    "Tongan Pa'anga",
    "Tongan Pa\u2019anga",
    "U.S. Dollar",
    "Ukrainian Hryvnia",
    "United Arab Emirates Dirham",
    "United States Dollar",
    "Uruguayan Peso",
    "Uzbekistani Som",
    "Vanuatu Vatu",
    "Venezuelan Bolivar",
    "Vietnamese Dong",
    "West African CFA Franc",
    "Yuan",
)

# Each currency, current or withdrawn: its code, its number, None where it has none, and a name;
# those of `pycountry` are typed as of any type, so that the tuples below say they are of texts.
_CURRENCIES: Final = (
    *(
        (currency.alpha_3, currency.numeric, currency.name)
        for currency in currencies
        if currency.alpha_3 not in _NONE
    ),
    *_WITHDRAWN,
)

CODES: Final[tuple[str, ...]] = tuple(sorted({code for code, _, _ in _CURRENCIES}))
"""The alphabetic codes of the currencies, in capitals, `EUR`, sorted."""

NUMBERS: Final[tuple[str, ...]] = tuple(
    sorted({number for _, number, _ in _CURRENCIES if number is not None})
)
"""The numbers of the currencies, of three digits, `978`, sorted."""

NAMES: Final[tuple[str, ...]] = tuple(
    sorted({name for _, _, name in _CURRENCIES if name not in _WORDS} | set(_COMMON))
)
"""The English names of the currencies, of ISO 4217 and more common ones, `Euro`, sorted."""
