"use client";

import React, { useState, useMemo } from "react";
import tickersListData from "@/data/tickers_list.json";
import sectorsSummaryData from "@/data/sectors_summary.json";
import { 
  Award, 
  Search, 
  SlidersHorizontal, 
  Download, 
  TrendingUp, 
  CheckCircle, 
  Sparkles, 
  Filter, 
  Zap, 
  ArrowUpRight 
} from "lucide-react";

interface ScreenerTabProps {
  onSelectTicker: (ticker: string) => void;
}

export default function ScreenerTab({ onSelectTicker }: ScreenerTabProps) {
  const [minRoe, setMinRoe] = useState<number>(10);
  const [minRoa, setMinRoa] = useState<number>(5);
  const [minReturn, setMinReturn] = useState<number>(0);
  const [selectedSector, setSelectedSector] = useState<string>("ALL");
  const [searchTicker, setSearchTicker] = useState<string>("");

  // Presets chiến lược đầu tư kinh điển
  const applyPreset = (preset: "buffett" | "growth" | "safe" | "reset") => {
    if (preset === "buffett") {
      setMinRoe(18);
      setMinRoa(8);
      setMinReturn(5);
      setSelectedSector("ALL");
    } else if (preset === "growth") {
      setMinRoe(15);
      setMinRoa(6);
      setMinReturn(20);
      setSelectedSector("ALL");
    } else if (preset === "safe") {
      setMinRoe(12);
      setMinRoa(7);
      setMinReturn(0);
      setSelectedSector("ALL");
    } else {
      setMinRoe(0);
      setMinRoa(0);
      setMinReturn(-50);
      setSelectedSector("ALL");
      setSearchTicker("");
    }
  };

  // Tính toán và lọc danh sách cổ phiếu
  const screenedList = useMemo(() => {
    return tickersListData
      .map((t) => {
        const roe = t.latest_roe ?? 0;
        const roa = t.latest_roa ?? 0;
        const ret = t.latest_return ?? 0;

        // Tính điểm Composite Score (0-100): ROE 40%, ROA 30%, Return 30%
        const roeScore = Math.min(Math.max((roe / 25) * 40, 0), 40);
        const roaScore = Math.min(Math.max((roa / 12) * 30, 0), 30);
        const retScore = Math.min(Math.max(((ret + 10) / 40) * 30, 0), 30);
        const score = Math.round(roeScore + roaScore + retScore);

        return {
          ...t,
          score
        };
      })
      .filter((t) => {
        const matchSearch = t.ticker.toLowerCase().includes(searchTicker.toLowerCase());
        const matchSector = selectedSector === "ALL" || t.sector_key === selectedSector;
        const matchRoe = (t.latest_roe ?? 0) >= minRoe;
        const matchRoa = (t.latest_roa ?? 0) >= minRoa;
        const matchReturn = (t.latest_return ?? 0) >= minReturn;

        return matchSearch && matchSector && matchRoe && matchRoa && matchReturn;
      })
      .sort((a, b) => b.score - a.score);
  }, [minRoe, minRoa, minReturn, selectedSector, searchTicker]);

  // Xuất file CSV
  const handleExportCSV = () => {
    const headers = ["Xếp hạng", "Mã CP", "Ngành", "Điểm Factor Score (0-100)", "ROE (%)", "ROA (%)", "Lợi nhuận năm (%)"];
    const rows = screenedList.map((t, idx) => [
      idx + 1,
      t.ticker,
      `"${t.sector_label}"`,
      t.score,
      t.latest_roe ?? "",
      t.latest_roa ?? "",
      t.latest_return ?? ""
    ]);

    const csvContent = "\uFEFF" + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `VNSTOCK_Screener_Results_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-8 animate-fadeIn w-full">
      
      {/* Header Banner */}
      <div className="color-card p-6 sm:p-10 rounded-3xl bg-gradient-to-r from-[#181138] via-[#101A3D] to-[#121B2F] border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/15 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-xs font-bold mb-4 shadow-sm">
            <Award className="w-4 h-4 text-purple-400" />
            <span>ADVANCED QUANTITATIVE FACTOR SCREENER</span>
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight">
            Bộ Lọc Cổ phiếu <br />
            <span className="text-gradient-aurora">Đa Nhân tố Toàn diện</span>
          </h1>

          <p className="mt-3 text-sm sm:text-base text-gray-300 leading-relaxed max-w-3xl">
            Sàng lọc tự động 50 mã cổ phiếu lớn nhất thị trường theo các tiêu chí định lượng chuẩn mực. Tùy chỉnh thanh trượt hoặc kích hoạt ngay các chiến lược đầu tư kinh điển của Warren Buffett, Benjamin Graham và CANSLIM.
          </p>
        </div>
      </div>

      {/* Preset Strategy Buttons */}
      <div className="color-card p-5 sm:p-6 rounded-3xl border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">
            Chiến lược định lượng mẫu 1-chạm:
          </span>
          <p className="text-xs text-gray-300 mt-0.5">Tự động cấu hình bộ lọc theo các trường phái đầu tư lừng danh thế giới</p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => applyPreset("buffett")}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/40 text-amber-300 hover:scale-105 transition-all shadow-sm"
          >
            💎 Warren Buffett (ROE &ge; 18%)
          </button>

          <button
            onClick={() => applyPreset("growth")}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/40 text-cyan-300 hover:scale-105 transition-all shadow-sm"
          >
            🚀 Tăng trưởng Cao (Return &ge; 20%)
          </button>

          <button
            onClick={() => applyPreset("safe")}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/40 text-emerald-300 hover:scale-105 transition-all shadow-sm"
          >
            🛡️ An toàn Sinh lời (ROA &ge; 7%)
          </button>

          <button
            onClick={() => applyPreset("reset")}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 text-gray-300 transition-colors"
          >
            Đặt lại
          </button>
        </div>
      </div>

      {/* Interactive Sliders & Filters Panel */}
      <div className="color-card p-6 sm:p-8 rounded-3xl card-glow-purple space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          
          {/* Slider 1: ROE */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-gray-300 uppercase">ROE tối thiểu:</span>
              <span className="font-mono font-bold text-purple-400 text-sm">{minRoe}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="35"
              step="1"
              value={minRoe}
              onChange={(e) => setMinRoe(Number(e.target.value))}
              className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
            />
            <span className="text-[10px] text-gray-500 block">Sinh lời trên vốn chủ sở hữu</span>
          </div>

          {/* Slider 2: ROA */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-gray-300 uppercase">ROA tối thiểu:</span>
              <span className="font-mono font-bold text-cyan-400 text-sm">{minRoa}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="20"
              step="1"
              value={minRoa}
              onChange={(e) => setMinRoa(Number(e.target.value))}
              className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <span className="text-[10px] text-gray-500 block">Sinh lời trên tổng tài sản</span>
          </div>

          {/* Slider 3: Return */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-gray-300 uppercase">Tỷ suất sinh lời:</span>
              <span className="font-mono font-bold text-emerald-400 text-sm">{minReturn}%</span>
            </div>
            <input
              type="range"
              min="-20"
              max="40"
              step="2"
              value={minReturn}
              onChange={(e) => setMinReturn(Number(e.target.value))}
              className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
            />
            <span className="text-[10px] text-gray-500 block">Lợi nhuận cổ phiếu cả năm</span>
          </div>

          {/* Dropdown Sector & Search */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-gray-300 uppercase">Lọc theo ngành:</label>
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              className="w-full bg-[#080D1A] border border-gray-700 text-white text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-purple-400 font-sans"
            >
              <option value="ALL">Tất cả 10 ngành</option>
              {sectorsSummaryData.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label} ({s.key})
                </option>
              ))}
            </select>
          </div>

        </div>

        {/* Filter Results Status Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-white/10 text-xs">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Tìm mã cổ phiếu..."
                value={searchTicker}
                onChange={(e) => setSearchTicker(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-[#080D1A] border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-400 font-mono uppercase w-40"
              />
            </div>
            <span className="text-gray-400">
              Tìm thấy <strong className="text-cyan-300">{screenedList.length}</strong> / 50 cổ phiếu thỏa mãn
            </span>
          </div>

          <button
            onClick={handleExportCSV}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-400 hover:to-emerald-500 text-white font-bold text-xs shadow-md shadow-teal-500/20 transition-all shrink-0"
          >
            <Download className="w-4 h-4" />
            <span>Xuất file CSV ({screenedList.length} mã)</span>
          </button>
        </div>
      </div>

      {/* Screener Results Table */}
      <div className="color-card p-6 sm:p-8 rounded-3xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#090D1C]/90 text-gray-300 font-bold uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="py-3.5 px-3 text-center">Hạng</th>
                <th className="py-3.5 px-3">Mã CP</th>
                <th className="py-3.5 px-3">Ngành kinh tế</th>
                <th className="py-3.5 px-3 text-right">ROE (%)</th>
                <th className="py-3.5 px-3 text-right">ROA (%)</th>
                <th className="py-3.5 px-3 text-right">Lợi nhuận năm</th>
                <th className="py-3.5 px-3 text-center">Điểm Factor Score</th>
                <th className="py-3.5 px-3 text-center">Chi tiết</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/80">
              {screenedList.map((item, idx) => (
                <tr
                  key={item.ticker}
                  onClick={() => onSelectTicker(item.ticker)}
                  className="hover:bg-white/5 cursor-pointer transition-colors group"
                >
                  <td className="py-3.5 px-3 text-center">
                    {idx === 0 ? (
                      <span className="inline-block px-2 py-0.5 rounded-full bg-amber-500 text-black font-black text-xs shadow-md shadow-amber-500/30">#1</span>
                    ) : idx === 1 ? (
                      <span className="inline-block px-2 py-0.5 rounded-full bg-slate-300 text-black font-black text-xs">#2</span>
                    ) : idx === 2 ? (
                      <span className="inline-block px-2 py-0.5 rounded-full bg-amber-700 text-white font-black text-xs">#3</span>
                    ) : (
                      <span className="text-gray-500 font-bold">#{idx + 1}</span>
                    )}
                  </td>

                  <td className="py-3.5 px-3 font-bold text-white text-sm group-hover:text-cyan-300 transition-colors">
                    {item.ticker}
                  </td>

                  <td className="py-3.5 px-3 font-sans text-gray-300">
                    {item.sector_label}
                  </td>

                  <td className="py-3.5 px-3 text-right text-emerald-400 font-bold text-sm">
                    {item.latest_roe}%
                  </td>

                  <td className="py-3.5 px-3 text-right text-cyan-300 font-bold text-sm">
                    {item.latest_roa}%
                  </td>

                  <td className={`py-3.5 px-3 text-right font-bold text-sm ${(item.latest_return ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {item.latest_return != null ? `${item.latest_return > 0 ? "+" : ""}${item.latest_return}%` : "N/A"}
                  </td>

                  <td className="py-3.5 px-3 text-center">
                    <div className="inline-flex items-center space-x-1 px-3 py-1 rounded-full bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border border-purple-500/40 text-purple-300 font-black shadow-sm">
                      <span>{item.score} / 100</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-3 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectTicker(item.ticker);
                      }}
                      className="p-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500 text-cyan-300 hover:text-white transition-all shadow-sm"
                      title="Mở hồ sơ cổ phiếu"
                    >
                      <ArrowUpRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
