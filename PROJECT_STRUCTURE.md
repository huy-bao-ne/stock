# Project Structure

Generated on: 2026-06-25
Scope: full workspace tree (max depth = 4)
Excluded: .git, venv, __pycache__, .mypy_cache, .pytest_cache, .vscode

```text
./
|-- factor/
|   |-- .streamlit/
|   |   \-- config.toml
|   |-- agents/
|   |   |-- api_server.py
|   |   \-- financial_agent.py
|   |-- analysis/
|   |   \-- correlation_engine.py
|   |-- collectors/
|   |   \-- vnstock_collector.py
|   |-- configs/
|   |   \-- config.yaml
|   |-- data/
|   |   |-- banking/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_BID_balance.csv
|   |   |   |-- raw_BID_cashflow.csv
|   |   |   |-- raw_BID_income.csv
|   |   |   |-- raw_CTG_balance.csv
|   |   |   |-- raw_CTG_cashflow.csv
|   |   |   |-- raw_CTG_income.csv
|   |   |   |-- raw_financial.json
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_TCB_balance.csv
|   |   |   |-- raw_TCB_cashflow.csv
|   |   |   |-- raw_TCB_income.csv
|   |   |   |-- raw_VCB_balance.csv
|   |   |   |-- raw_VCB_cashflow.csv
|   |   |   |-- raw_VCB_income.csv
|   |   |   |-- raw_VPB_balance.csv
|   |   |   |-- raw_VPB_cashflow.csv
|   |   |   |-- raw_VPB_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- chemicals/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_BMP_balance.csv
|   |   |   |-- raw_BMP_cashflow.csv
|   |   |   |-- raw_BMP_income.csv
|   |   |   |-- raw_DCM_balance.csv
|   |   |   |-- raw_DCM_cashflow.csv
|   |   |   |-- raw_DCM_income.csv
|   |   |   |-- raw_DGC_balance.csv
|   |   |   |-- raw_DGC_cashflow.csv
|   |   |   |-- raw_DGC_income.csv
|   |   |   |-- raw_DPM_balance.csv
|   |   |   |-- raw_DPM_cashflow.csv
|   |   |   |-- raw_DPM_income.csv
|   |   |   |-- raw_GVR_balance.csv
|   |   |   |-- raw_GVR_cashflow.csv
|   |   |   |-- raw_GVR_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   \-- yearly_return.csv
|   |   |-- construction/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_HUT_balance.csv
|   |   |   |-- raw_HUT_cashflow.csv
|   |   |   |-- raw_HUT_income.csv
|   |   |   |-- raw_LGC_balance.csv
|   |   |   |-- raw_LGC_cashflow.csv
|   |   |   |-- raw_LGC_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_REE_balance.csv
|   |   |   |-- raw_REE_cashflow.csv
|   |   |   |-- raw_REE_income.csv
|   |   |   |-- raw_THD_balance.csv
|   |   |   |-- raw_THD_cashflow.csv
|   |   |   |-- raw_THD_income.csv
|   |   |   |-- raw_VCG_balance.csv
|   |   |   |-- raw_VCG_cashflow.csv
|   |   |   |-- raw_VCG_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- food/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_MCH_balance.csv
|   |   |   |-- raw_MCH_cashflow.csv
|   |   |   |-- raw_MCH_income.csv
|   |   |   |-- raw_MSN_balance.csv
|   |   |   |-- raw_MSN_cashflow.csv
|   |   |   |-- raw_MSN_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_SAB_balance.csv
|   |   |   |-- raw_SAB_cashflow.csv
|   |   |   |-- raw_SAB_income.csv
|   |   |   |-- raw_SBT_balance.csv
|   |   |   |-- raw_SBT_cashflow.csv
|   |   |   |-- raw_SBT_income.csv
|   |   |   |-- raw_VNM_balance.csv
|   |   |   |-- raw_VNM_cashflow.csv
|   |   |   |-- raw_VNM_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- healthcare/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_DBD_balance.csv
|   |   |   |-- raw_DBD_cashflow.csv
|   |   |   |-- raw_DBD_income.csv
|   |   |   |-- raw_DHG_balance.csv
|   |   |   |-- raw_DHG_cashflow.csv
|   |   |   |-- raw_DHG_income.csv
|   |   |   |-- raw_DHT_balance.csv
|   |   |   |-- raw_DHT_cashflow.csv
|   |   |   |-- raw_DHT_income.csv
|   |   |   |-- raw_IMP_balance.csv
|   |   |   |-- raw_IMP_cashflow.csv
|   |   |   |-- raw_IMP_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_TRA_balance.csv
|   |   |   |-- raw_TRA_cashflow.csv
|   |   |   |-- raw_TRA_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- master/
|   |   |   \-- master_index.csv
|   |   |-- realestate/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_BCM_balance.csv
|   |   |   |-- raw_BCM_cashflow.csv
|   |   |   |-- raw_BCM_income.csv
|   |   |   |-- raw_KSF_balance.csv
|   |   |   |-- raw_KSF_cashflow.csv
|   |   |   |-- raw_KSF_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_VHM_balance.csv
|   |   |   |-- raw_VHM_cashflow.csv
|   |   |   |-- raw_VHM_income.csv
|   |   |   |-- raw_VIC_balance.csv
|   |   |   |-- raw_VIC_cashflow.csv
|   |   |   |-- raw_VIC_income.csv
|   |   |   |-- raw_VRE_balance.csv
|   |   |   |-- raw_VRE_cashflow.csv
|   |   |   |-- raw_VRE_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- securities/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_HCM_balance.csv
|   |   |   |-- raw_HCM_cashflow.csv
|   |   |   |-- raw_HCM_income.csv
|   |   |   |-- raw_MBS_balance.csv
|   |   |   |-- raw_MBS_cashflow.csv
|   |   |   |-- raw_MBS_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_SSI_balance.csv
|   |   |   |-- raw_SSI_cashflow.csv
|   |   |   |-- raw_SSI_income.csv
|   |   |   |-- raw_VCI_balance.csv
|   |   |   |-- raw_VCI_cashflow.csv
|   |   |   |-- raw_VCI_income.csv
|   |   |   |-- raw_VND_balance.csv
|   |   |   |-- raw_VND_cashflow.csv
|   |   |   |-- raw_VND_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- technology/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_CMG_balance.csv
|   |   |   |-- raw_CMG_cashflow.csv
|   |   |   |-- raw_CMG_income.csv
|   |   |   |-- raw_CTR_balance.csv
|   |   |   |-- raw_CTR_cashflow.csv
|   |   |   |-- raw_CTR_income.csv
|   |   |   |-- raw_ELC_balance.csv
|   |   |   |-- raw_ELC_cashflow.csv
|   |   |   |-- raw_ELC_income.csv
|   |   |   |-- raw_FPT_balance.csv
|   |   |   |-- raw_FPT_cashflow.csv
|   |   |   |-- raw_FPT_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_SGT_balance.csv
|   |   |   |-- raw_SGT_cashflow.csv
|   |   |   |-- raw_SGT_income.csv
|   |   |   \-- yearly_return.csv
|   |   |-- transport/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   |-- gold_factors.csv
|   |   |   |-- raw_GMD_balance.csv
|   |   |   |-- raw_GMD_cashflow.csv
|   |   |   |-- raw_GMD_income.csv
|   |   |   |-- raw_HVN_balance.csv
|   |   |   |-- raw_HVN_cashflow.csv
|   |   |   |-- raw_HVN_income.csv
|   |   |   |-- raw_prices.csv
|   |   |   |-- raw_PVT_balance.csv
|   |   |   |-- raw_PVT_cashflow.csv
|   |   |   |-- raw_PVT_income.csv
|   |   |   |-- raw_VJC_balance.csv
|   |   |   |-- raw_VJC_cashflow.csv
|   |   |   |-- raw_VJC_income.csv
|   |   |   |-- raw_VTP_balance.csv
|   |   |   |-- raw_VTP_cashflow.csv
|   |   |   |-- raw_VTP_income.csv
|   |   |   \-- yearly_return.csv
|   |   \-- utilities/
|   |       |-- bảng_cân_đối_kế_toán.csv
|   |       |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |       |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |       |-- gold_factors.csv
|   |       |-- raw_GAS_balance.csv
|   |       |-- raw_GAS_cashflow.csv
|   |       |-- raw_GAS_income.csv
|   |       |-- raw_IDC_balance.csv
|   |       |-- raw_IDC_cashflow.csv
|   |       |-- raw_IDC_income.csv
|   |       |-- raw_PGV_balance.csv
|   |       |-- raw_PGV_cashflow.csv
|   |       |-- raw_PGV_income.csv
|   |       |-- raw_POW_balance.csv
|   |       |-- raw_POW_cashflow.csv
|   |       |-- raw_POW_income.csv
|   |       |-- raw_prices.csv
|   |       |-- raw_SIP_balance.csv
|   |       |-- raw_SIP_cashflow.csv
|   |       |-- raw_SIP_income.csv
|   |       \-- yearly_return.csv
|   |-- factors/
|   |   \-- factor_builder.py
|   |-- outputs/
|   |   |-- banking/
|   |   |   |-- banking_factor_results.csv
|   |   |   \-- banking_ticker_results.csv
|   |   |-- chemicals/
|   |   |   |-- chemicals_factor_results.csv
|   |   |   \-- chemicals_ticker_results.csv
|   |   |-- construction/
|   |   |   |-- construction_factor_results.csv
|   |   |   \-- construction_ticker_results.csv
|   |   |-- food/
|   |   |   |-- food_factor_results.csv
|   |   |   \-- food_ticker_results.csv
|   |   |-- healthcare/
|   |   |   |-- healthcare_factor_results.csv
|   |   |   \-- healthcare_ticker_results.csv
|   |   |-- realestate/
|   |   |   |-- realestate_factor_results.csv
|   |   |   \-- realestate_ticker_results.csv
|   |   |-- securities/
|   |   |   |-- securities_factor_results.csv
|   |   |   \-- securities_ticker_results.csv
|   |   |-- technology/
|   |   |   |-- technology_factor_results.csv
|   |   |   \-- technology_ticker_results.csv
|   |   |-- transport/
|   |   |   |-- transport_factor_results.csv
|   |   |   \-- transport_ticker_results.csv
|   |   \-- utilities/
|   |       |-- utilities_factor_results.csv
|   |       \-- utilities_ticker_results.csv
|   |-- processors/
|   |   |-- banking_processor.py
|   |   |-- base_processor.py
|   |   |-- nonbanking_processor.py
|   |   |-- price_processor.py
|   |   \-- processor_factory.py
|   |-- ui/
|   |   \-- app.py
|   |-- utils/
|   |   \-- master_index.py
|   |-- visualization/
|   |   \-- factor_chart.py
|   |-- .env
|   |-- main.py
|   |-- README.md
|   \-- requirements.txt
|-- news/
|   |-- runtime_data/
|   |   |-- data_warehouse.json
|   |   \-- smart_watchlist.json
|   |-- advanced_quant.py
|   |-- agent1_collector.py
|   |-- api.py
|   |-- cache_test.txt
|   |-- index.html
|   |-- quant_engine.py
|   |-- requirements.txt
|   |-- server.log
|   |-- trend_calculator.py
|   \-- utils.py
|-- test/
|   |-- banking/
|   |   |-- data/
|   |   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |   \-- stock.docx
|   |   |-- src/
|   |   |   |-- extract/
|   |   |   |-- pipeline/
|   |   |   |-- transform/
|   |   |   \-- __init__.py
|   |   |-- config.py
|   |   |-- main.py
|   |   |-- README_FINISHED.md
|   |   \-- VIEW_RAW_DATA.py
|   |-- data/
|   |   |-- all_tickers.csv
|   |   |-- available_tickers_2024.csv
|   |   |-- bảng_cân_đối_kế_toán.csv
|   |   |-- banking_factor_results.csv
|   |   |-- banking_ticker_results.csv
|   |   |-- báo_cáo_kết_quả_kinh_doanh.csv
|   |   |-- báo_cáo_lưu_chuyển_tiền_tệ.csv
|   |   |-- chungkhoang.md
|   |   |-- financial_processor.py
|   |   |-- gold_factors.csv
|   |   |-- industry_candidates.csv
|   |   |-- industry_count.csv
|   |   |-- industry_summary.csv
|   |   |-- listed_tickers.csv
|   |   |-- market_cap_data.csv
|   |   |-- master_company_list.csv
|   |   |-- raw_prices.csv
|   |   |-- top5_each_industry.csv
|   |   |-- VCB_balance_sheet.csv
|   |   |-- VCB_cash_flow.csv
|   |   |-- VCB_income_statement.csv
|   |   |-- VCB_ratio.csv
|   |   \-- yearly_return.csv
|   |-- check.py
|   |-- count.py
|   |-- docs.md
|   |-- PROJECT_STRUCTURE.md
|   |-- stock.py
|   |-- test.py
|   |-- ticker.py
|   |-- weekly_presentation_banking.md
|   \-- weekly_report_week1.md
|-- .gitignore
\-- README.md
```
