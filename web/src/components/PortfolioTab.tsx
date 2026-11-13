"use client";

import React, { useState, useMemo } from "react";
import tickersListData from "@/data/tickers_list.json";
import tickersDetailData from "@/data/tickers_detail.json";
import { 
  Briefcase, 
  TrendingUp, 
  DollarSign, 
  Percent, 
  RotateCcw, 
  ShieldAlert, 
  Plus, 
  Trash2, 
  Sparkles, 
  Award,
  Layers,
  ArrowRight
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  AreaChart,
  Area
} from "recharts";

interface Allocation {
  ticker: string;
  weight: number; // percentage (0 - 100)
}

export default function PortfolioTab() {
  const [initialCapital, setInitialCapital] = useState<number>(100); // triệu VNĐ
  const [allocations, setAllocations] = useState<Allocation[]>([
    { ticker: "FPT", weight: 40 },
    { ticker: "VCB", weight: 30 },
    { ticker: "HPG", weight: 30 },
  ]);

  // Các danh mục gợi ý sẵn (Presets)
  const portfolioPresets = [
    {
      name: "Tăng trưởng Công nghệ & Ngân hàng",
      desc: "FPT (40%), VCB (30%), TCB (30%)",
      alloc: [
        { ticker: "FPT", weight: 40 },
        { ticker: "VCB", weight: 30 },
        { ticker: "TCB", weight: 30 },
      ]
    },
    {
      name: "Đầu tư Cân bằng Bền vững",
      desc: "VCB (25%), FPT (25%), HPG (25%), VNM (25%)",
      alloc: [
        { ticker: "VCB", weight: 25 },
        { ticker: "FPT", weight: 25 },
        { ticker: "HPG", weight: 25 },
        { ticker: "VNM", weight: 25 },
      ]
    },
    {
      name: "Phòng thủ Cổ tức & Tiện ích",
      desc: "GAS (40%), REE (30%), DHG (30%)",
      alloc: [
        { ticker: "GAS", weight: 40 },
        { ticker: "REE", weight: 30 },
        { ticker: "DHG", weight: 30 },
      ]
    }
  ];

  // Tổng tỷ trọng
  const totalWeight = allocations.reduce((sum, item) => sum + item.weight, 0);

  // Thêm cổ phiếu vào danh mục
  const handleAddStock = (ticker: string) => {
    if (allocations.find(a => a.ticker === ticker)) return;
    if (allocations.length >= 6) return;
    const remainingWeight = Math.max(0, 100 - totalWeight);
    setAllocations([...allocations, { ticker, weight: remainingWeight > 0 ? remainingWeight : 10 }]);
  };

  // Xóa cổ phiếu
  const handleRemoveStock = (ticker: string) => {
    if (allocations.length <= 1) return;
    setAllocations(allocations.filter(a => a.ticker !== ticker));
  };

  // Cập nhật tỷ trọng
  const handleWeightChange = (ticker: string, newWeight: number) => {
    setAllocations(allocations.map(a => a.ticker === ticker ? { ...a, weight: Math.max(0, Math.min(100, newWeight)) } : a));
  };

  // Tự động chuẩn hóa về 100%
  const handleNormalizeWeights = () => {
    if (allocations.length === 0) return;
    const currentSum = allocations.reduce((sum, a) => sum + a.weight, 0);
    if (currentSum === 0) {
      const equal = Math.floor(100 / allocations.length);
      setAllocations(allocations.map((a, i) => ({ ...a, weight: i === 0 ? 100 - equal * (allocations.length - 1) : equal })));
    } else {
      setAllocations(allocations.map(a => ({ ...a, weight: Math.round((a.weight / currentSum) * 100) })));
    }
  };

  // Tính toán Backtest tăng trưởng tài sản chuỗi thời gian 2018 - 2024
  const backtestResults = useMemo(() => {
    const years = [2018, 2019, 2020, 2021, 2022, 2023, 2024];
    let portfolioValue = initialCapital;
    let benchmarkValue = initialCapital; // VN-Index tham chiếu giả định ~9.5%/năm

    const trajectory = [{
      year: "2018 (Bắt đầu)",
      portfolio: initialCapital,
      benchmark: initialCapital,
      annualReturn: 0
    }];

    // Lấy dữ liệu return của từng ticker qua các năm
    const tickerReturns: Record<string, Record<number, number>> = {};
    allocations.forEach(a => {
      const yearly = (tickersDetailData as any)[a.ticker]?.yearly_data || [];
      tickerReturns[a.ticker] = {};
      yearly.forEach((d: any) => {
        if (d["lợi_nhuận_hàng_năm_%"] != null) {
          tickerReturns[a.ticker][d.year] = parseFloat(Number(d["lợi_nhuận_hàng_năm_%"]).toFixed(2));
        }
      });
    });

    let peakValue = initialCapital;
    let maxDrawdown = 0;

    for (let i = 1; i < years.length; i++) {
      const yr = years[i];
      let weightedYearReturn = 0;
      let effectiveWeightSum = 0;

      allocations.forEach(a => {
        const ret = tickerReturns[a.ticker]?.[yr] ?? 0;
        weightedYearReturn += ret * (a.weight / 100);
        effectiveWeightSum += a.weight;
      });

      // Nếu tổng weight khác 100, chuẩn hóa lại
      if (effectiveWeightSum > 0 && effectiveWeightSum !== 100) {
        weightedYearReturn = weightedYearReturn * (100 / effectiveWeightSum);
      }

      portfolioValue = portfolioValue * (1 + weightedYearReturn / 100);
      
      // Giả định VN-Index biến động thực tế qua các năm: 2019 (+7.7%), 2020 (+14.9%), 2021 (+35.7%), 2022 (-32.8%), 2023 (+12.2%), 2024 (+11.5%)
      const vnIndexReturns: Record<number, number> = {
        2019: 7.7,
        2020: 14.9,
        2021: 35.7,
        2022: -32.8,
        2023: 12.2,
        2024: 11.5
      };
      const bRet = vnIndexReturns[yr] ?? 10;
      benchmarkValue = benchmarkValue * (1 + bRet / 100);

      // Tính Drawdown
      if (portfolioValue > peakValue) {
        peakValue = portfolioValue;
      } else {
        const dd = ((peakValue - portfolioValue) / peakValue) * 100;
        if (dd > maxDrawdown) maxDrawdown = dd;
      }

      trajectory.push({
        year: yr.toString(),
        portfolio: Math.round(portfolioValue * 10) / 10,
        benchmark: Math.round(benchmarkValue * 10) / 10,
        annualReturn: Math.round(weightedYearReturn * 10) / 10
      });
    }

    // Tỷ suất sinh lời kép hàng năm (CAGR)
    const totalReturnPercent = ((portfolioValue - initialCapital) / initialCapital) * 100;
    const numYears = years.length - 1; // 6 năm
    const cagr = (Math.pow(portfolioValue / initialCapital, 1 / numYears) - 1) * 100;

    return {
      trajectory,
      finalValue: Math.round(portfolioValue * 10) / 10,
      totalProfit: Math.round((portfolioValue - initialCapital) * 10) / 10,
      totalReturnPercent: Math.round(totalReturnPercent * 10) / 10,
      cagr: Math.round(cagr * 10) / 10,
      maxDrawdown: Math.round(maxDrawdown * 10) / 10,
      benchmarkFinal: Math.round(benchmarkValue * 10) / 10
    };
  }, [allocations, initialCapital]);

  return (
    <div className="space-y-8 animate-fadeIn w-full">
      
      {/* Header Banner */}
      <div className="color-card p-6 sm:p-10 rounded-3xl bg-gradient-to-r from-[#141A38] via-[#10233D] to-[#121B2F] border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/15 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-bold mb-4 shadow-sm">
            <Briefcase className="w-4 h-4 text-cyan-400" />
            <span>PORTFOLIO BACKTESTING & FACTOR SIMULATOR (2018–2024)</span>
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight">
            Mô phỏng & Kiểm thử <br />
            <span className="text-gradient-aurora">Danh mục Đầu tư Thực chiến</span>
          </h1>

          <p className="mt-3 text-sm sm:text-base text-gray-300 leading-relaxed max-w-3xl">
            Tự tay phân bổ tỷ trọng các cổ phiếu yêu thích và mô phỏng số vốn đầu tư ban đầu sẽ tăng trưởng thế nào từ 2018 đến 2024. Đo lường tỷ suất sinh lời kép (CAGR), so sánh với chỉ số VN-Index và kiểm soát mức sụt giảm tối đa (Max Drawdown).
          </p>
        </div>
      </div>

      {/* Preset Strategy Chips */}
      <div className="color-card p-5 sm:p-6 rounded-3xl border border-white/10 space-y-3">
        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">
          Chọn nhanh Danh mục mẫu do Chuyên gia định lượng thiết kế:
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {portfolioPresets.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => setAllocations(preset.alloc)}
              className="p-4 rounded-2xl bg-[#090E1F] hover:bg-white/10 border border-white/10 hover:border-cyan-500/40 text-left transition-all group shadow-sm"
            >
              <div className="text-xs font-bold text-white group-hover:text-cyan-300 transition-colors">
                {preset.name}
              </div>
              <div className="text-[11px] text-gray-400 mt-1 font-mono">
                {preset.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Grid: Portfolio Configuration (Left) & Key Performance Cards (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Ticker Allocation Manager (1/3) */}
        <div className="color-card p-6 sm:p-8 rounded-3xl card-glow-cyan space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <span>Cấu trúc Danh mục</span>
              </h3>
              <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-xl border ${
                totalWeight === 100 
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" 
                  : "bg-amber-500/20 text-amber-300 border-amber-500/40"
              }`}>
                Tổng: {totalWeight}%
              </span>
            </div>

            {/* Input Capital */}
            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase mb-2">
                Vốn đầu tư ban đầu (Triệu VNĐ):
              </label>
              <input
                type="number"
                min="10"
                max="100000"
                step="10"
                value={initialCapital}
                onChange={(e) => setInitialCapital(Math.max(1, Number(e.target.value)))}
                className="w-full bg-[#080D1A] border border-cyan-500/40 text-cyan-300 font-mono font-bold text-lg rounded-xl px-4 py-2.5 focus:outline-none focus:border-cyan-400"
              />
            </div>

            {/* Allocation List */}
            <div className="space-y-3 pt-2">
              <label className="block text-xs font-bold text-gray-400 uppercase">
                Phân bổ tỷ trọng các mã (Tối đa 6 mã):
              </label>

              {allocations.map((item) => (
                <div key={item.ticker} className="p-3 bg-black/40 rounded-2xl border border-white/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-black text-white text-sm">{item.ticker}</span>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono font-bold text-cyan-300">{item.weight}%</span>
                      {allocations.length > 1 && (
                        <button
                          onClick={() => handleRemoveStock(item.ticker)}
                          className="p-1 rounded-lg hover:bg-rose-500/20 text-gray-500 hover:text-rose-400 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={item.weight}
                    onChange={(e) => handleWeightChange(item.ticker, Number(e.target.value))}
                    className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                  />
                </div>
              ))}
            </div>

            {/* Add stock & Normalize */}
            <div className="flex items-center space-x-2 pt-2">
              <select
                onChange={(e) => {
                  if (e.target.value) {
                    handleAddStock(e.target.value);
                    e.target.value = "";
                  }
                }}
                className="flex-1 bg-[#090D1C] border border-gray-700 text-white text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-cyan-400 font-mono"
              >
                <option value="">+ Thêm mã cổ phiếu...</option>
                {tickersListData
                  .filter(t => !allocations.some(a => a.ticker === t.ticker))
                  .map(t => (
                    <option key={t.ticker} value={t.ticker}>
                      {t.ticker} ({t.sector_label})
                    </option>
                  ))}
              </select>

              <button
                onClick={handleNormalizeWeights}
                className="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-gray-200 text-xs font-bold transition-all shrink-0"
                title="Tự động chia đều hoặc cân bằng tỷ trọng về 100%"
              >
                Cân bằng 100%
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Performance Summary Scorecards & Charts (2/3) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* 4 Scorecards KPI */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            
            <div className="color-card p-5 rounded-3xl card-glow-emerald bg-gradient-to-br from-emerald-950/40 to-[#0A1020]">
              <span className="text-[10px] font-bold uppercase text-emerald-300">Giá trị Hiện tại (2024)</span>
              <div className="text-2xl sm:text-3xl font-black text-emerald-300 font-mono mt-1">
                {backtestResults.finalValue} <span className="text-xs font-normal">tr</span>
              </div>
              <p className="text-[11px] text-emerald-400/80 mt-1">
                Lợi nhuận: +{backtestResults.totalProfit} tr ({backtestResults.totalReturnPercent > 0 ? "+" : ""}{backtestResults.totalReturnPercent}%)
              </p>
            </div>

            <div className="color-card p-5 rounded-3xl card-glow-cyan bg-gradient-to-br from-cyan-950/40 to-[#0A1020]">
              <span className="text-[10px] font-bold uppercase text-cyan-300">Tỷ suất Kép (CAGR)</span>
              <div className="text-2xl sm:text-3xl font-black text-cyan-200 font-mono mt-1">
                {backtestResults.cagr}% <span className="text-xs font-normal">/năm</span>
              </div>
              <p className="text-[11px] text-cyan-400/80 mt-1">Sinh lời đều đặn 6 năm</p>
            </div>

            <div className="color-card p-5 rounded-3xl card-glow-amber bg-gradient-to-br from-amber-950/40 to-[#0A1020]">
              <span className="text-[10px] font-bold uppercase text-amber-300">So với VN-Index</span>
              <div className="text-2xl sm:text-3xl font-black text-amber-200 font-mono mt-1">
                {backtestResults.finalValue > backtestResults.benchmarkFinal ? (
                  <span className="text-emerald-400">+{Math.round(backtestResults.finalValue - backtestResults.benchmarkFinal)} tr</span>
                ) : (
                  <span className="text-rose-400">{Math.round(backtestResults.finalValue - backtestResults.benchmarkFinal)} tr</span>
                )}
              </div>
              <p className="text-[11px] text-amber-400/80 mt-1">VN-Index đạt {backtestResults.benchmarkFinal} tr</p>
            </div>

            <div className="color-card p-5 rounded-3xl card-glow-rose bg-gradient-to-br from-rose-950/40 to-[#0A1020]">
              <span className="text-[10px] font-bold uppercase text-rose-300">Max Drawdown</span>
              <div className="text-2xl sm:text-3xl font-black text-rose-300 font-mono mt-1">
                -{backtestResults.maxDrawdown}%
              </div>
              <p className="text-[11px] text-rose-400/80 mt-1">Mức giảm sâu nhất từ đỉnh</p>
            </div>

          </div>

          {/* Area Chart: Wealth Growth Over Time */}
          <div className="color-card p-6 sm:p-8 rounded-3xl card-glow-cyan">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">Đường Cong Tăng trưởng Tài sản (2018–2024)</h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Đường màu xanh ngọc: Danh mục của bạn · Đường nét đứt xám: Thị trường chung VN-Index
                </p>
              </div>
              <div className="text-xs font-mono text-cyan-300 px-3 py-1 bg-cyan-500/10 rounded-xl border border-cyan-500/30">
                Vốn ban đầu: {initialCapital} Triệu
              </div>
            </div>

            <div className="w-full h-84">
              <ResponsiveContainer width="100%" height={340}>
                <AreaChart
                  data={backtestResults.trajectory}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <defs>
                    <linearGradient id="colorPortfolio" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#22304E" />
                  <XAxis dataKey="year" stroke="#CBD5E1" fontSize={11} />
                  <YAxis stroke="#94A3B8" fontSize={11} unit=" tr" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0E1528",
                      borderColor: "#334155",
                      borderRadius: "14px",
                      color: "#F8FAFC",
                      fontSize: "12px",
                      boxShadow: "0 10px 30px -5px rgba(0,0,0,0.7)"
                    }}
                    formatter={(val: number) => [`${val} Triệu VNĐ`]}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  <Area
                    type="monotone"
                    dataKey="portfolio"
                    name="Danh mục Đầu tư của bạn"
                    stroke="#06B6D4"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorPortfolio)"
                  />
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    name="Chỉ số VN-Index Tham chiếu"
                    stroke="#94A3B8"
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
