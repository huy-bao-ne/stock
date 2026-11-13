"use client";

import React, { useState } from "react";
import sectorsSummaryData from "@/data/sectors_summary.json";
import { 
  TrendingUp, 
  CheckCircle2, 
  BarChart3, 
  Database, 
  ArrowRight, 
  Filter, 
  Search,
  ShieldCheck,
  Award,
  Zap,
  ArrowUpRight,
  Flame,
  Sparkles
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid
} from "recharts";

interface OverviewTabProps {
  onSelectSector: (sectorKey: string) => void;
}

export default function OverviewTab({ onSelectSector }: OverviewTabProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [onlyBonferroni, setOnlyBonferroni] = useState(false);

  // Tính toán KPI
  const totalSectors = sectorsSummaryData.length;
  const totalFactorsTested = sectorsSummaryData.reduce((acc, cur) => acc + cur.factors_tested, 0);
  const totalBonferroniSig = sectorsSummaryData.reduce((acc, cur) => acc + cur.significant_bonferroni, 0);
  const avgObs = Math.round(
    sectorsSummaryData.reduce((acc, cur) => acc + cur.observations_max, 0) / (totalSectors || 1)
  );

  // Map màu sắc nhận diện riêng cho từng ngành
  const sectorColors: Record<string, { badge: string; border: string; glow: string }> = {
    BANKING: { badge: "bg-blue-500/20 text-blue-300 border-blue-500/40", border: "border-blue-500", glow: "from-blue-600/30 to-cyan-600/10" },
    REALESTATE: { badge: "bg-purple-500/20 text-purple-300 border-purple-500/40", border: "border-purple-500", glow: "from-purple-600/30 to-pink-600/10" },
    TECHNOLOGY: { badge: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40", border: "border-cyan-500", glow: "from-cyan-600/30 to-blue-600/10" },
    FOOD: { badge: "bg-orange-500/20 text-orange-300 border-orange-500/40", border: "border-orange-500", glow: "from-orange-600/30 to-red-600/10" },
    CONSTRUCTION: { badge: "bg-amber-500/20 text-amber-300 border-amber-500/40", border: "border-amber-500", glow: "from-amber-600/30 to-yellow-600/10" },
    TRANSPORT: { badge: "bg-teal-500/20 text-teal-300 border-teal-500/40", border: "border-teal-500", glow: "from-teal-600/30 to-emerald-600/10" },
    CHEMICALS: { badge: "bg-pink-500/20 text-pink-300 border-pink-500/40", border: "border-pink-500", glow: "from-pink-600/30 to-rose-600/10" },
    UTILITIES: { badge: "bg-lime-500/20 text-lime-300 border-lime-500/40", border: "border-lime-500", glow: "from-lime-600/30 to-emerald-600/10" },
    SECURITIES: { badge: "bg-indigo-500/20 text-indigo-300 border-indigo-500/40", border: "border-indigo-500", glow: "from-indigo-600/30 to-purple-600/10" },
    HEALTHCARE: { badge: "bg-rose-500/20 text-rose-300 border-rose-500/40", border: "border-rose-500", glow: "from-rose-600/30 to-pink-600/10" },
  };

  // Lọc bảng
  const filteredData = sectorsSummaryData.filter((item) => {
    const matchSearch =
      item.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.key.toLowerCase().includes(searchTerm.toLowerCase());
    const matchBonf = onlyBonferroni ? item.significant_bonferroni > 0 : true;
    return matchSearch && matchBonf;
  });

  // Top 3 Ngành có Factor mạnh nhất
  const topSectors = [...sectorsSummaryData]
    .sort((a, b) => Math.abs(b.top_correlation_value) - Math.abs(a.top_correlation_value))
    .slice(0, 3);

  // Dữ liệu biểu đồ Bonferroni đa sắc
  const chartData = [...sectorsSummaryData]
    .map(s => ({
      name: s.label,
      key: s.key,
      bonferroni: s.significant_bonferroni,
      p05: s.significant_p05,
    }))
    .sort((a, b) => b.bonferroni - a.bonferroni);

  const barPalette = [
    "#06B6D4", "#8B5CF6", "#10B981", "#F59E0B", "#EC4899", 
    "#3B82F6", "#14B8A6", "#F97316", "#6366F1", "#84CC16"
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Hero Banner Rực rỡ Sắc màu */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#111936] via-[#1A103C] to-[#1F122B] border border-white/15 p-8 md:p-12 shadow-2xl">
        {/* Glow Spheres */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-gradient-to-br from-cyan-500/30 via-purple-500/25 to-pink-500/20 rounded-full blur-3xl pointer-events-none animate-pulse"></div>
        <div className="absolute bottom-0 left-10 -mb-16 w-80 h-80 bg-gradient-to-tr from-emerald-500/20 to-teal-500/20 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-gradient-to-r from-cyan-500/20 via-purple-500/20 to-pink-500/20 border border-white/20 text-white text-xs font-bold mb-5 shadow-lg backdrop-blur-md">
            <Sparkles className="w-4 h-4 text-cyan-300 animate-spin-slow" />
            <span className="tracking-wider bg-gradient-to-r from-cyan-300 via-teal-200 to-pink-300 bg-clip-text text-transparent">
              QUANTITATIVE FINANCE 2018–2024 · VIETNAM STOCK MARKET
            </span>
          </div>

          <h1 className="text-3xl sm:text-5xl md:text-6xl font-black text-white tracking-tight leading-tight">
            Ma trận Phân tích Nhân tố <br />
            <span className="text-gradient-aurora">
              10 Ngành Kinh tế Trọng điểm
            </span>
          </h1>

          <p className="mt-5 text-sm sm:text-base text-gray-200 leading-relaxed max-w-2xl font-normal">
            Khám phá sức mạnh tương quan định lượng giữa các chỉ số BCTC và tỷ suất sinh lời cổ phiếu Việt Nam. Kiểm định <strong className="text-cyan-300">Bonferroni Correction</strong> đảm bảo kết quả chống false-positive với độ tin cậy khoa học cao nhất.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              onClick={() => onSelectSector("TECHNOLOGY")}
              className="flex items-center space-x-2.5 px-6 py-3 rounded-2xl bg-gradient-to-r from-cyan-500 via-teal-500 to-emerald-500 hover:scale-105 text-white font-bold text-xs sm:text-sm shadow-xl shadow-cyan-500/30 transition-all duration-300 group"
            >
              <Zap className="w-4 h-4" />
              <span>Khám phá Ngành Công nghệ</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1.5 transition-transform" />
            </button>

            <button
              onClick={() => onSelectSector("BANKING")}
              className="flex items-center space-x-2 px-5 py-3 rounded-2xl bg-white/10 hover:bg-white/15 border border-white/15 text-white font-bold text-xs sm:text-sm transition-all"
            >
              <span>Xem Ngành Ngân hàng</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 KPI Cards Sống động & Đa sắc */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        
        {/* Card 1: Cyan / Sky */}
        <div className="color-card p-6 rounded-3xl card-glow-cyan bg-gradient-to-br from-cyan-950/40 via-[#0F1A30] to-[#080D1A]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">Ngành kinh tế</span>
            <div className="p-2.5 rounded-2xl bg-cyan-500/20 text-cyan-300 shadow-md shadow-cyan-500/20">
              <Database className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 text-3xl md:text-4xl font-black text-cyan-200 font-mono tracking-tight">
            {totalSectors}
          </div>
          <div className="mt-2 text-xs text-cyan-400 font-medium">
            10 ngành phân tích toàn diện
          </div>
        </div>

        {/* Card 2: Purple / Violet */}
        <div className="color-card p-6 rounded-3xl card-glow-purple bg-gradient-to-br from-purple-950/40 via-[#181133] to-[#080D1A]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-purple-300">Factors đã test</span>
            <div className="p-2.5 rounded-2xl bg-purple-500/20 text-purple-300 shadow-md shadow-purple-500/20">
              <BarChart3 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 text-3xl md:text-4xl font-black text-purple-200 font-mono tracking-tight">
            {totalFactorsTested}
          </div>
          <div className="mt-2 text-xs text-purple-400 font-medium">
            Sinh lời · Tăng trưởng · Đòn bẩy
          </div>
        </div>

        {/* Card 3: Emerald / Mint */}
        <div className="color-card p-6 rounded-3xl card-glow-emerald bg-gradient-to-br from-emerald-950/40 via-[#0C241E] to-[#080D1A]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-300">Chuẩn Bonferroni</span>
            <div className="p-2.5 rounded-2xl bg-emerald-500/20 text-emerald-300 shadow-md shadow-emerald-500/20">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 text-3xl md:text-4xl font-black text-emerald-300 font-mono tracking-tight">
            {totalBonferroniSig}
          </div>
          <div className="mt-2 text-xs text-emerald-400 font-medium">
            Ý nghĩa thống kê vững chắc
          </div>
        </div>

        {/* Card 4: Amber / Gold */}
        <div className="color-card p-6 rounded-3xl card-glow-amber bg-gradient-to-br from-amber-950/40 via-[#261B0E] to-[#080D1A]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-300">Mẫu quan sát TB</span>
            <div className="p-2.5 rounded-2xl bg-amber-500/20 text-amber-300 shadow-md shadow-amber-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 text-3xl md:text-4xl font-black text-amber-200 font-mono tracking-tight">
            {avgObs}
          </div>
          <div className="mt-2 text-xs text-amber-400 font-medium">
            Quan sát 7 năm (2018–2024)
          </div>
        </div>

      </div>

      {/* Top 3 Gold Factors Spotlight Sắc màu */}
      <div className="color-card p-6 sm:p-8 rounded-3xl border border-amber-500/30 bg-gradient-to-br from-[#1A1528] via-[#0E1528] to-[#120F24]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
            <Award className="w-5 h-5 text-amber-400 animate-bounce" />
            <span>TOP 3 NHÂN TỐ VÀNG (GOLD FACTORS) TOÀN THỊ TRƯỜNG</span>
          </div>
          <span className="text-xs text-amber-300 font-semibold hidden sm:inline">Tương quan cao nhất</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {topSectors.map((sec, idx) => {
            const glowStyles = [
              "border-amber-500/50 from-amber-500/15 via-[#1D162B] to-[#0D1322]",
              "border-cyan-500/50 from-cyan-500/15 via-[#102038] to-[#0D1322]",
              "border-purple-500/50 from-purple-500/15 via-[#1E1136] to-[#0D1322]"
            ];

            return (
              <div
                key={sec.key}
                onClick={() => onSelectSector(sec.key)}
                className={`p-5 rounded-2xl bg-gradient-to-b ${glowStyles[idx]} border hover:scale-[1.02] cursor-pointer transition-all duration-300 shadow-lg group`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-black/40 text-white border border-white/10">
                    {sec.label}
                  </span>
                  <span className={`text-xs font-bold font-mono px-2.5 py-1 rounded-full shadow-sm ${
                    sec.top_correlation_value > 0 ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"
                  }`}>
                    {sec.top_correlation}
                  </span>
                </div>
                <p className="text-sm font-extrabold text-white group-hover:text-cyan-300 transition-colors line-clamp-2">
                  {sec.top_factor}
                </p>
                <div className="mt-4 flex items-center justify-between text-xs text-gray-300 font-mono pt-3 border-t border-white/10">
                  <span>Mẫu: {sec.observations_max} quan sát</span>
                  <span className="flex items-center text-cyan-300 font-sans font-bold group-hover:translate-x-1 transition-transform">
                    Khám phá <ArrowUpRight className="w-4 h-4 ml-0.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Biểu đồ & Bảng 10 Ngành Rực rỡ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Chart (1/3) */}
        <div className="color-card p-6 sm:p-8 rounded-3xl flex flex-col card-glow-emerald">
          <div className="mb-4">
            <h3 className="font-extrabold text-white text-base flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></span>
              <span>Significant Factors (Bonferroni)</span>
            </h3>
            <p className="text-xs text-gray-400 mt-1">
              Số nhân tố đạt kiểm định khắt khe nhất theo từng ngành
            </p>
          </div>

          <div className="flex-1 w-full min-h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 10, right: 30, left: 40, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#263352" horizontal={false} />
                <XAxis type="number" stroke="#94A3B8" fontSize={11} allowDecimals={false} />
                <YAxis dataKey="name" type="category" stroke="#E2E8F0" fontSize={11} width={95} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0E1528",
                    borderColor: "#334155",
                    borderRadius: "14px",
                    color: "#F8FAFC",
                    fontSize: "12px",
                    boxShadow: "0 10px 30px -5px rgba(0,0,0,0.7)"
                  }}
                  formatter={(val: number) => [`${val} factors`, "Chuẩn Bonferroni"]}
                />
                <Bar dataKey="bonferroni" radius={[0, 8, 8, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.bonferroni > 0 ? barPalette[index % barPalette.length] : "#1E293B"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Column: Bảng 10 Ngành Đa sắc (2/3) */}
        <div className="lg:col-span-2 color-card p-6 sm:p-8 rounded-3xl flex flex-col card-glow-cyan">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h3 className="font-extrabold text-white text-base">Bảng Xếp hạng 10 Ngành Kinh tế</h3>
              <p className="text-xs text-gray-400 mt-1">
                Bấm vào từng ngành để xem toàn bộ danh mục chỉ số và biểu đồ tương quan
              </p>
            </div>

            {/* Filter controls */}
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Tìm tên ngành..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8 pr-3 py-1.5 bg-[#090D1A] border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 w-36 sm:w-44"
                />
              </div>

              <button
                onClick={() => setOnlyBonferroni(!onlyBonferroni)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                  onlyBonferroni
                    ? "bg-gradient-to-r from-emerald-500 to-teal-600 text-white border-transparent shadow-lg shadow-emerald-500/25"
                    : "bg-[#090D1A] text-gray-300 border-gray-700 hover:text-white"
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
                <span>Bonferroni {">"} 0</span>
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#090D1A]/90 text-gray-300 font-bold uppercase tracking-wider border-b border-gray-800">
                <tr>
                  <th className="py-3.5 px-3">Ngành</th>
                  <th className="py-3.5 px-3 text-center">Factors</th>
                  <th className="py-3.5 px-3 text-center">p &lt; 0.05</th>
                  <th className="py-3.5 px-3 text-center">Bonferroni</th>
                  <th className="py-3.5 px-3">Factor mạnh nhất</th>
                  <th className="py-3.5 px-3 text-right">Tương quan</th>
                  <th className="py-3.5 px-3 text-center">Khám phá</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/80 font-mono">
                {filteredData.map((item) => {
                  const sColor = sectorColors[item.key] || { badge: "bg-gray-800 text-gray-300 border-gray-700", border: "border-gray-700", glow: "" };

                  return (
                    <tr
                      key={item.key}
                      onClick={() => onSelectSector(item.key)}
                      className="hover:bg-white/5 cursor-pointer transition-colors group"
                    >
                      <td className="py-3.5 px-3 font-sans">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold border ${sColor.badge}`}>
                          {item.label}
                        </span>
                        <span className="block text-[10px] text-gray-500 font-mono mt-0.5">{item.key}</span>
                      </td>

                      <td className="py-3.5 px-3 text-center text-gray-200 font-bold">
                        {item.factors_tested}
                      </td>

                      <td className="py-3.5 px-3 text-center text-cyan-300 font-extrabold">
                        {item.significant_p05}
                      </td>

                      <td className="py-3.5 px-3 text-center">
                        {item.significant_bonferroni > 0 ? (
                          <span className="inline-block px-2.5 py-0.5 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-extrabold text-[11px] shadow-md shadow-emerald-500/20">
                            {item.significant_bonferroni}
                          </span>
                        ) : (
                          <span className="text-gray-600">0</span>
                        )}
                      </td>

                      <td className="py-3.5 px-3 font-sans text-gray-200 font-semibold truncate max-w-[170px]" title={item.top_factor}>
                        {item.top_factor}
                      </td>

                      <td className="py-3.5 px-3 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          {/* Visual Progress Bar Gradient */}
                          <div className="w-14 h-2 rounded-full bg-gray-800 overflow-hidden hidden sm:block">
                            <div
                              className={`h-full rounded-full ${
                                item.top_correlation_value > 0 
                                  ? "bg-gradient-to-r from-teal-400 to-emerald-400" 
                                  : "bg-gradient-to-r from-rose-400 to-red-500"
                              }`}
                              style={{ width: `${Math.min(Math.abs(item.top_correlation_value), 100)}%` }}
                            />
                          </div>
                          <span
                            className={`font-black ${
                              item.top_correlation_value > 0
                                ? "text-emerald-400"
                                : item.top_correlation_value < 0
                                ? "text-rose-400"
                                : "text-gray-400"
                            }`}
                          >
                            {item.top_correlation}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectSector(item.key);
                          }}
                          className="p-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:scale-110 transition-all shadow-md shadow-cyan-500/20"
                          title="Xem chi tiết ngành"
                        >
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

      </div>

    </div>
  );
}
