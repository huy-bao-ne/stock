"""
processors/nonbanking_processor.py
====================================
Processor cho các sector NON-BANKING: Real Estate, Technology, Food & Beverage.

Kiến trúc:
  NonBankingProcessor      ← Base: chỉ chứa item_ids CHUNG cho mọi ngành
    ├── RealEstateProcessor ← Thêm: đặt cọc KH, xây dựng dở dang
    ├── TechnologyProcessor ← Thêm: quỹ phát triển KHCN (R&D)
    └── FoodProcessor       ← Thêm: không có item_id đặc thù
                               Factor builder tính inventory_turnover từ IS+BS

item_ids CHUNG (tất cả non-banking đều có):
  Balance Sheet  : bsa1, bsa2, bsa8, bsa15, bsa16, bsa23, bsa29,
                   bsa53, bsa54, bsa55, bsa56, bsa57, bsa67, bsa71,
                   bsa78, bsa80, bsa90
  Income Statement: isa1, isa3, isa5, isa6, isa7, isa10, isa11,
                    isa15, isa16, isa19, isa20, isa23
  Cash Flow      : cfa18, cfa19, cfa26, cfa32, cfa34, cfa36, cfa38

item_ids ĐẶC THÙ theo ngành:
  Real Estate : bsa58 (đặt cọc KH), bsa188 (xây dựng dở dang)
  Technology  : bsa77 (quỹ phát triển KHCN / R&D fund)
  Food        : (không có — inventory turnover tính từ isa3 / bsa16)
"""

from processors.base_processor import BaseFinancialProcessor


# ======================================================================
# BASE — chỉ item_ids CHUNG, không có gì đặc thù ngành
# ======================================================================

class NonBankingProcessor(BaseFinancialProcessor):
    """
    Base processor cho RE, Tech, Food.
    Chỉ khai báo item_ids và growth targets CHUNG.
    Subclass override để thêm item_ids đặc thù ngành.
    """

    # ------------------------------------------------------------------
    # BALANCE SHEET — chung
    # ------------------------------------------------------------------
    @property
    def balance_item_map(self) -> dict:
        return {
            # === TÀI SẢN NGẮN HẠN ===
            "bsa1":  "tài_sản_ngắn_hạn",
            "bsa2":  "tiền_và_tương_đương_tiền",
            "bsa8":  "phải_thu_ngắn_hạn",
            "bsa15": "hàng_tồn_kho",           # gross — dùng để verify
            "bsa16": "hàng_tồn_kho_net",        # net (sau dự phòng) — dùng cho growth & turnover
            # === TÀI SẢN DÀI HẠN ===
            "bsa23": "tài_sản_dài_hạn",
            "bsa29": "tài_sản_cố_định",
            # === TỔNG ===
            "bsa53": "tổng_tài_sản",
            # === NỢ PHẢI TRẢ ===
            "bsa54": "tổng_nợ_phải_trả",
            "bsa55": "nợ_ngắn_hạn",
            "bsa56": "vay_ngắn_hạn",
            "bsa57": "phải_trả_người_bán_ngắn_hạn",
            "bsa67": "nợ_dài_hạn",
            "bsa71": "vay_dài_hạn",
            # === VỐN CHỦ SỞ HỮU ===
            "bsa78": "tổng_vốn_chủ_sở_hữu",
            "bsa80": "vốn_điều_lệ",
            "bsa90": "lợi_nhuận_giữ_lại",
        }

    # ------------------------------------------------------------------
    # INCOME STATEMENT — chung
    # ------------------------------------------------------------------
    @property
    def income_item_map(self) -> dict:
        return {
            "isa1":  "doanh_thu_bán_hàng",
            "isa3":  "doanh_thu_thuần",         # dùng cho revenue growth & inventory turnover
            "isa5":  "lợi_nhuận_gộp",
            "isa6":  "chi_phí_tài_chính",
            "isa7":  "chi_phí_lãi_vay",
            "isa10": "chi_phí_bán_hàng",
            "isa11": "chi_phí_quản_lý",
            "isa15": "lợi_nhuận_từ_hđkd",
            "isa16": "lợi_nhuận_trước_thuế",
            "isa19": "chi_phí_thuế",
            "isa20": "lợi_nhuận_sau_thuế",
            "isa23": "eps_cơ_bản",              # VNĐ — base_processor tự giữ nguyên đơn vị
        }

    # ------------------------------------------------------------------
    # CASH FLOW — chung
    # ------------------------------------------------------------------
    @property
    def cashflow_item_map(self) -> dict:
        return {
            "cfa18": "lưu_chuyển_tiền_hđkd",
            "cfa19": "mua_sắm_tscđ",            # CapEx, âm
            "cfa26": "lưu_chuyển_tiền_hđ_đầu_tư",
            "cfa32": "cổ_tức_đã_trả",
            "cfa34": "lưu_chuyển_tiền_thuần_trong_kỳ",
            "cfa36": "tiền_đầu_kỳ",
            "cfa38": "tiền_cuối_kỳ",
        }

    # ------------------------------------------------------------------
    # GROWTH TARGETS — chung
    # ------------------------------------------------------------------

    def _bs_growth_targets(self) -> list:
        return [
            "tổng_tài_sản",
            "hàng_tồn_kho_net",
            "tổng_vốn_chủ_sở_hữu",
            "vay_ngắn_hạn",
            "vay_dài_hạn",
            "tài_sản_ngắn_hạn",
            "tài_sản_dài_hạn",
        ]

    def _inc_growth_targets(self) -> list:
        return [
            "doanh_thu_thuần",
            "lợi_nhuận_gộp",
            "lợi_nhuận_từ_hđkd",
            "lợi_nhuận_sau_thuế",
            "eps_cơ_bản",
        ]

    def _cf_growth_targets(self) -> list:
        return [
            "lưu_chuyển_tiền_hđkd",
        ]


# ======================================================================
# REAL ESTATE — thêm đặt cọc KH + xây dựng dở dang
# ======================================================================

class RealEstateProcessor(NonBankingProcessor):
    """
    Real Estate: BĐS dở dang → inventory growth quan trọng.
    Factor đặc thù:
      - bsa58  : Người mua trả tiền trước (đặt cọc KH) → demand indicator
      - bsa188 : Xây dựng cơ bản đang dở dang → pipeline dự án
    Factor builder tính thêm: tỷ_lệ_đặt_cọc_% = bsa58 / bsa53
    """

    @property
    def balance_item_map(self) -> dict:
        base = super().balance_item_map.copy()
        base.update({
            "bsa58":  "người_mua_trả_tiền_trước",  # RE: đặt cọc KH
            "bsa188": "xây_dựng_dở_dang",           # RE: pipeline dự án
        })
        return base

    def _bs_growth_targets(self) -> list:
        return super()._bs_growth_targets() + [
            "người_mua_trả_tiền_trước",
            "xây_dựng_dở_dang",
        ]


# ======================================================================
# TECHNOLOGY — thêm quỹ R&D
# ======================================================================

class TechnologyProcessor(NonBankingProcessor):
    """
    Technology: revenue growth và margin là key factors.
    Factor đặc thù:
      - bsa77 : Quỹ phát triển khoa học công nghệ (R&D fund)
    Factor builder tính thêm: tỷ_lệ_rd_% = bsa77 / bsa53
    """

    @property
    def balance_item_map(self) -> dict:
        base = super().balance_item_map.copy()
        base.update({
            "bsa77": "quỹ_phát_triển_khcn",    # Tech: R&D fund
        })
        return base

    def _bs_growth_targets(self) -> list:
        return super()._bs_growth_targets() + [
            "quỹ_phát_triển_khcn",
        ]


# ======================================================================
# FOOD & BEVERAGE — không có item_id đặc thù
# ======================================================================

class FoodProcessor(NonBankingProcessor):
    """
    Food & Beverage: gross margin và inventory turnover là key.
    Không có item_id đặc thù — dùng chung với base.
    Factor builder tính thêm:
      - inventory_turnover = doanh_thu_thuần / hàng_tồn_kho_net
        (vòng quay tồn kho — cao = bán nhanh = tốt)
    """
    pass


# ======================================================================
# 6 NGÀNH MỚI — dùng chung NonBankingProcessor base
# Không có item_id đặc thù — factor builder xử lý phần còn lại
# ======================================================================

class ConstructionProcessor(NonBankingProcessor):
    """Xây dựng: revenue growth, asset turnover, debt ratio là key."""
    pass

class TransportProcessor(NonBankingProcessor):
    """Vận tải - Kho bãi: asset turnover, cash flow growth là key."""
    pass

class ChemicalsProcessor(NonBankingProcessor):
    """SX Nhựa - Hóa chất: gross margin, inventory turnover là key."""
    pass

class UtilitiesProcessor(NonBankingProcessor):
    """Tiện ích: ROA, ROE, debt ratio là key (vốn lớn, dòng tiền ổn định)."""
    pass

class SecuritiesProcessor(NonBankingProcessor):
    """
    Chứng khoán: cấu trúc báo cáo tài chính ĐẶC THÙ — dùng prefix iss thay vì isa.
    
    Balance Sheet: giống non-banking (bsa prefix) — giữ nguyên base
    Income Statement: dùng iss prefix (Securities-specific)
      - iss42  : Doanh thu môi giới
      - iss44  : Doanh thu bảo lãnh phát hành  
      - iss46  : Doanh thu tư vấn đầu tư
      - iss47  : Doanh thu lưu ký
      - iss115 : Lãi từ tài sản tài chính FVTPL
      - iss141 : Doanh thu hoạt động tài chính
    + giữ lại isa20 (LN sau thuế), isa23 (EPS) từ base
    """

    @property
    def income_item_map(self) -> dict:
        return {
            # === DOANH THU ĐẶC THÙ CHỨNG KHOÁN ===
            "isa1":   "doanh_thu_hoạt_động",          # tổng doanh thu
            "isa3":   "doanh_thu_thuần",               # doanh thu thuần
            "isa5":   "lợi_nhuận_gộp",
            "isa10":  "chi_phí_quản_lý",               # chi phí quản lý CTCK
            "isa11":  "kết_quả_hoạt_động",             # operating profit
            # Doanh thu từng nghiệp vụ
            "iss42":  "doanh_thu_môi_giới",
            "iss44":  "doanh_thu_bảo_lãnh",
            "iss46":  "doanh_thu_tư_vấn",
            "iss47":  "doanh_thu_lưu_ký",
            "iss115": "lãi_tài_sản_fvtpl",             # lãi từ đầu tư FVTPL
            "iss141": "doanh_thu_tài_chính",           # tổng doanh thu tài chính
            # === LỢI NHUẬN (giống non-banking) ===
            "isa20":  "lợi_nhuận_sau_thuế",
            "isa22":  "lợi_nhuận_cổ_đông_công_ty_mẹ",
            "isa23":  "eps_cơ_bản",
        }

    def _inc_growth_targets(self) -> list:
        return [
            "doanh_thu_thuần",
            "lợi_nhuận_gộp",
            "kết_quả_hoạt_động",
            "lợi_nhuận_sau_thuế",
            "doanh_thu_môi_giới",      # Securities-specific: growth môi giới
            "doanh_thu_tài_chính",     # Securities-specific: growth tài chính
            "eps_cơ_bản",
        ]

class HealthcareProcessor(NonBankingProcessor):
    """Chăm sóc sức khỏe: gross margin, net margin, ROE là key."""
    pass


# ======================================================================
# FACTORY
# ======================================================================

PROCESSOR_MAP = {
    "REALESTATE":  RealEstateProcessor,
    "TECHNOLOGY":  TechnologyProcessor,
    "FOOD":        FoodProcessor,
    "CONSTRUCTION": ConstructionProcessor,
    "TRANSPORT":   TransportProcessor,
    "CHEMICALS":   ChemicalsProcessor,
    "UTILITIES":   UtilitiesProcessor,
    "SECURITIES":  SecuritiesProcessor,
    "HEALTHCARE":  HealthcareProcessor,
}

def get_nonbanking_processor(sector: str, **kwargs) -> NonBankingProcessor:
    """
    Trả về đúng processor cho sector.
    """
    cls = PROCESSOR_MAP.get(sector.upper(), NonBankingProcessor)
    return cls(**kwargs)