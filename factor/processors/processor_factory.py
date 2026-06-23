"""
processors/processor_factory.py
=================================
Factory: trả về đúng processor theo sector name.

Cách dùng:
    from processors.processor_factory import get_processor
    processor = get_processor("BANKING")
    processor = get_processor("CONSTRUCTION")
"""

from processors.banking_processor    import get_banking_processor
from processors.nonbanking_processor import get_nonbanking_processor

# Các sector dùng NonBankingProcessor
NONBANKING_SECTORS = {
    "REALESTATE", "TECHNOLOGY", "FOOD",
    "CONSTRUCTION", "TRANSPORT", "CHEMICALS",
    "UTILITIES", "SECURITIES", "HEALTHCARE",
}

def get_processor(sector: str, **kwargs):
    """
    Trả về processor phù hợp cho sector.

    Parameters
    ----------
    sector : 'BANKING', 'REALESTATE', 'TECHNOLOGY', 'FOOD',
             'CONSTRUCTION', 'TRANSPORT', 'CHEMICALS',
             'UTILITIES', 'SECURITIES', 'HEALTHCARE'
    kwargs : unit_divisor, round_decimals (truyền xuống processor)
    """
    s = sector.upper()

    if s == "BANKING":
        return get_banking_processor(**kwargs)

    if s in NONBANKING_SECTORS:
        return get_nonbanking_processor(s, **kwargs)

    raise ValueError(
        f"Sector '{sector}' chưa được hỗ trợ. "
        f"Hiện có: BANKING + {sorted(NONBANKING_SECTORS)}"
    )