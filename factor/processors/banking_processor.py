"""
processors/banking_processor.py
================================
Processor cho sector Banking.

Kế thừa BaseFinancialProcessor — chỉ cần khai báo:
  - ITEM_ID_MAP cho 3 bảng (dùng bsb prefix cho Banking-specific items)
  - growth targets cho từng bảng

item_id reference (từ VCB mẫu thực tế):
  Balance Sheet:
    bsa2   Tiền mặt, vàng bạc
    bsa29  Tài sản cố định
    bsa53  TỔNG TÀI SẢN
    bsa54  TỔNG NỢ PHẢI TRẢ
    bsa78  VỐN CHỦ SỞ HỮU
    bsa80  Vốn điều lệ
    bsa90  Lợi nhuận chưa phân phối
    bsb97  Tiền gửi tại NHNN
    bsb98  Tiền gửi tại TCTD khác (tổng)
    bsb103 Cho vay khách hàng (net)
    bsb104 Cho vay khách hàng (gross)
    bsb105 Dự phòng rủi ro cho vay
    bsb106 Chứng khoán đầu tư
    bsb111 Nợ chính phủ và NHNN
    bsb112 Tiền gửi & vay TCTD khác (nợ)
    bsb113 Tiền gửi của khách hàng
    bsb116 Phát hành giấy tờ có giá
    bsb118 Vốn của TCTD
    bsb121 Quỹ của TCTD

  Income Statement:
    isa16  Lợi nhuận trước thuế
    isa19  Chi phí thuế TNDN
    isa20  Lợi nhuận sau thuế
    isa22  Cổ đông công ty mẹ
    isa23  EPS cơ bản
    isb25  Thu nhập lãi và tương đương
    isb26  Chi phí lãi và tương đương
    isb27  Thu nhập lãi thuần (NII)
    isb30  Lãi thuần dịch vụ
    isb38  Tổng thu nhập hoạt động (TOI)
    isb39  Chi phí quản lý doanh nghiệp
    isb40  Lợi nhuận trước dự phòng
    isb41  Trích lập dự phòng tổn thất tín dụng

  Cash Flow:
    cfa18  Lưu chuyển tiền thuần HĐKD
    cfa19  Mua sắm TSCĐ (CapEx, âm)
    cfa26  Lưu chuyển tiền thuần HĐ đầu tư
    cfa32  Cổ tức đã trả
    cfa36  Tiền đầu kỳ
    cfa38  Tiền cuối kỳ
"""

from processors.base_processor import BaseFinancialProcessor


class BankingProcessor(BaseFinancialProcessor):
    """
    Processor cho ngân hàng thương mại Việt Nam.
    Dùng item_id prefix bsb/isb (Banking-specific).
    """

    # ------------------------------------------------------------------
    # BALANCE SHEET item_id → tên cột tiếng Việt
    # ------------------------------------------------------------------
    @property
    def balance_item_map(self) -> dict:
        return {
            # === TÀI SẢN ===
            "bsa2":   "tiền_mặt_vàng_bạc",
            "bsa29":  "tài_sản_cố_định",
            "bsa53":  "tổng_tài_sản",
            "bsb97":  "tiền_gửi_tại_nhnn",
            "bsb98":  "tiền_gửi_tại_tctd_khác",        # tổng (gồm cả cho vay)
            "bsb103": "cho_vay_khách_hàng_net",          # sau dự phòng
            "bsb104": "cho_vay_khách_hàng",              # gross — dùng cho LDR
            "bsb105": "dự_phòng_rủi_ro_cho_vay",         # âm
            "bsb106": "chứng_khoán_đầu_tư",

            # === NỢ PHẢI TRẢ ===
            "bsa54":  "tổng_nợ_phải_trả",
            "bsb111": "nợ_chính_phủ_nhnn",
            "bsb112": "tiền_gửi_vay_tctd_khác",
            "bsb113": "tiền_gửi_khách_hàng",             # dùng cho LDR
            "bsb116": "giấy_tờ_có_giá_phát_hành",

            # === VỐN CHỦ SỞ HỮU ===
            "bsa78":  "tổng_vốn_chủ_sở_hữu",
            "bsa80":  "vốn_điều_lệ",
            "bsa90":  "lợi_nhuận_giữ_lại",
            "bsb118": "vốn_tctd",
            "bsb121": "quỹ_tctd",
        }

    # ------------------------------------------------------------------
    # INCOME STATEMENT item_id → tên cột
    # ------------------------------------------------------------------
    @property
    def income_item_map(self) -> dict:
        return {
            # === THU NHẬP LÃI ===
            "isb25": "thu_nhập_lãi_và_tương_đương",
            "isb26": "chi_phí_lãi_và_tương_đương",       # âm
            "isb27": "thu_nhập_lãi_thuần",                # NII = isb25 + isb26

            # === THU NHẬP HOẠT ĐỘNG ===
            "isb30": "lãi_thuần_dịch_vụ",
            "isb38": "tổng_thu_nhập_hoạt_động",           # TOI

            # === CHI PHÍ & DỰ PHÒNG ===
            "isb39": "chi_phí_quản_lý",                   # âm (CIR = |isb39|/isb38)
            "isb40": "lợi_nhuận_trước_dự_phòng",
            "isb41": "chi_phí_dự_phòng_tín_dụng",         # âm

            # === LỢI NHUẬN ===
            "isa16": "lợi_nhuận_trước_thuế",
            "isa19": "chi_phí_thuế",                      # âm
            "isa20": "lợi_nhuận_sau_thuế",
            "isa22": "lợi_nhuận_cổ_đông_công_ty_mẹ",
            "isa23": "eps_cơ_bản",                        # VNĐ, không chia tỷ
        }

    # ------------------------------------------------------------------
    # CASH FLOW item_id → tên cột
    # ------------------------------------------------------------------
    @property
    def cashflow_item_map(self) -> dict:
        return {
            "cfa18": "lưu_chuyển_tiền_hđkd",
            "cfa19": "mua_sắm_tscđ",                      # CapEx, âm
            "cfa26": "lưu_chuyển_tiền_hđ_đầu_tư",
            "cfa32": "cổ_tức_đã_trả",                     # âm
            "cfa36": "tiền_đầu_kỳ",
            "cfa38": "tiền_cuối_kỳ",
        }

    # ------------------------------------------------------------------
    # GROWTH TARGETS — cột nào tính % YoY
    # ------------------------------------------------------------------

    def _bs_growth_targets(self) -> list:
        return [
            "tổng_tài_sản",
            "cho_vay_khách_hàng",           # gross loan growth
            "tiền_gửi_khách_hàng",          # deposit growth (factor nổi bật)
            "tổng_vốn_chủ_sở_hữu",
            "chứng_khoán_đầu_tư",
            "giấy_tờ_có_giá_phát_hành",
        ]

    def _inc_growth_targets(self) -> list:
        return [
            "thu_nhập_lãi_thuần",           # NII growth
            "tổng_thu_nhập_hoạt_động",      # TOI growth
            "lợi_nhuận_sau_thuế",
            "lợi_nhuận_trước_dự_phòng",
            "eps_cơ_bản",
        ]

    def _cf_growth_targets(self) -> list:
        return [
            "lưu_chuyển_tiền_hđkd",
        ]


# EPS cần xử lý đặc biệt — không chia tỷ
# Override _process_one để giữ nguyên đơn vị EPS
# Factory — dùng thẳng BankingProcessor vì base_processor đã xử lý EPS đúng
def get_banking_processor(**kwargs) -> BankingProcessor:
    return BankingProcessor(**kwargs)