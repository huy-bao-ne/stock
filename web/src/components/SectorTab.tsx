"use client";

import React, { useState } from "react";
import sectorsFactorsData from "@/data/sectors_factors.json";
import { 
  Layers, 
  Search, 
  CheckCircle, 
  Info,
  TrendingUp,
  TrendingDown,
  Building,
  Cpu,
  ShoppingBag,
  HardHat,
  Truck,
  FlaskConical,
  Zap,
  LineChart,
  HeartPulse,
  BrainCircuit,
  Sparkles,
  Award
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  CartesianGrid
} from "recharts";

interface SectorTabProps {
  selectedSector: string;
  onSelectSector: (sector: string) => void;
}

export default function SectorTab({ selectedSector, onSelectSector }: SectorTabProps) {
  const [filterMode, setFilterMode] = useState<"all" | "sig" | "bonf">("all");
  const [searchFactor, setSearchFactor] = useState("");

  const sectorsList = Object.keys(sectorsFactorsData) as Array<keyof typeof sectorsFactorsData>;
  const currentSectorData = sectorsFactorsData[selectedSector as keyof typeof sectorsFactorsData] || sectorsFactorsData["BANKING"];

  // Cấu hình icon và dải màu gradient riêng biệt cho từng ngành
  const sectorConfigs: Record<string, { icon: any; gradient: string; border: string; glow: string }> = {
    BANKING: { icon: Building, gradient: "from-blue-600 to-cyan-500", border: "border-blue-500", glow: "shadow-blue-500/25" },
    REALESTATE: { icon: Layers, gradient: "from-purple-600 to-pink-500", border: "border-purple-500", glow: "shadow-purple-500/25" },
    TECHNOLOGY: { icon: Cpu, gradient: "from-cyan-500 to-blue-600", border: "border-cyan-500", glow: "shadow-cyan-500/25" },
    FOOD: { icon: ShoppingBag, gradient: "from-orange-500 to-amber-500", border: "border-orange-500", glow: "shadow-orange-500/25" },
    CONSTRUCTION: { icon: HardHat, gradient: "from-amber-500 to-yellow-400", border: "border-amber-500", glow: "shadow-amber-500/25" },
    TRANSPORT: { icon: Truck, gradient: "from-teal-500 to-emerald-500", border: "border-teal-500", glow: "shadow-teal-500/25" },
    CHEMICALS: { icon: FlaskConical, gradient: "from-pink-500 to-rose-600", border: "border-pink-500", glow: "shadow-pink-500/25" },
    UTILITIES: { icon: Zap, gradient: "from-lime-400 to-emerald-600", border: "border-lime-500", glow: "shadow-lime-500/25" },
    SECURITIES: { icon: LineChart, gradient: "from-indigo-600 to-purple-600", border: "border-indigo-500", glow: "shadow-indigo-500/25" },
    HEALTHCARE: { icon: HeartPulse, gradient: "from-rose-500 to-pink-600", border: "border-rose-500", glow: "shadow-rose-500/25" },
  };

  // Lọc factors
  const filteredFactors = currentSectorData.factors.filter((f) => {
    const matchSearch = f.factor.toLowerCase().includes(searchFactor.toLowerCase());
    if (!matchSearch) return false;
    if (filterMode === "bonf") return f.is_bonferroni_sig;
    if (filterMode === "sig") return f.is_significant;
    return true;
  });

  // Top 15 factors cho biểu đồ
  const chartFactors = [...currentSectorData.factors]
    .slice(0, 15)
    .map(f => ({
      name: f.factor.length > 24 ? f.factor.slice(0, 22) + "..." : f.factor,
      fullName: f.factor,
      value: f.correlation_value,
      is_bonferroni: f.is_bonferroni_sig,
      is_significant: f.is_significant,
      p_value: f.p_value
    }));

  const activeConfig = sectorConfigs[selectedSector] || sectorConfigs["BANKING"];
  const SectorIcon = activeConfig.icon;

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* 10 Sectors Interactive Grid Selector Sống động */}
      <div className="color-card p-6 sm:p-8 rounded-3xl space-y-4 card-glow-purple">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-cyan-300 text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-cyan-400 animate-spin-slow" />
            <span>DANH MỤC 10 NGÀNH KINH TẾ (BẤM ĐỂ CHUYỂN NGÀNH)</span>
          </div>
          <span className="text-xs text-purple-300 font-semibold hidden sm:inline">Phân tích chuyên sâu 2018–2024</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {sectorsList.map((secKey) => {
            const conf = sectorConfigs[secKey] || sectorConfigs["BANKING"];
            const Icon = conf.icon;
            const isSelected = selectedSector === secKey;
            const secInfo = sectorsFactorsData[secKey];
            const bonfCount = secInfo.factors.filter(f => f.is_bonferroni_sig).length;

            return (
              <button
                key={secKey}
                onClick={() => onSelectSector(secKey)}
                className={`p-3.5 rounded-2xl text-left transition-all duration-300 border flex flex-col justify-between relative group ${
                  isSelected
                    ? `bg-gradient-to-br from-white/10 via-[#18233C] to-[#0A0E1A] ${conf.border} shadow-xl ${conf.glow} scale-[1.03]`
                    : "bg-[#090D1C] border-white/10 hover:border-white/25 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center justify-between mb-2.5">
                  <div className={`p-2.5 rounded-xl bg-gradient-to-tr ${conf.gradient} text-white shadow-md shadow-black/40`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  {bonfCount > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/25 text-emerald-300 font-mono font-black border border-emerald-500/40 shadow-sm">
                      {bonfCount} Bonf
                    </span>
                  )}
                </div>
                <div>
                  <div className={`text-xs font-black truncate ${isSelected ? "text-white" : "text-gray-300 group-hover:text-white"}`}>
                    {secInfo.label}
                  </div>
                  <div className="text-[10px] text-gray-500 font-mono mt-0.5">{secKey}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Sector Header Detail & AI Executive Take Rực rỡ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Sector Profile Header Card (1/3) */}
        <div className={`color-card p-6 sm:p-8 rounded-3xl flex flex-col justify-between bg-gradient-to-br from-[#121B33] via-[#0E1528] to-[#090E1A] border-t-4 ${activeConfig.border}`}>
          <div>
            <div className={`w-14 h-14 rounded-2xl bg-gradient-to-tr ${activeConfig.gradient} flex items-center justify-center text-white mb-4 shadow-xl ${activeConfig.glow}`}>
              <SectorIcon className="w-7 h-7" />
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">HỒ SƠ ĐỊNH LƯỢNG NGÀNH</span>
            <h2 className="text-3xl font-black text-white mt-1">{currentSectorData.label}</h2>
            <p className="text-xs text-gray-300 mt-2 leading-relaxed">
              Tập hợp dữ liệu tài chính BCTC chuẩn hóa từ 5 doanh nghiệp đầu ngành trong suốt chu kỳ 2018–2024.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-6 pt-6 border-t border-white/10 font-mono">
            <div className="bg-black/30 p-3 rounded-2xl border border-white/5">
              <span className="text-[10px] text-gray-400 uppercase font-bold">Tổng số Factors</span>
              <div className="text-xl font-black text-cyan-300 mt-1">{currentSectorData.factors.length}</div>
            </div>
            <div className="bg-black/30 p-3 rounded-2xl border border-white/5">
              <span className="text-[10px] text-gray-400 uppercase font-bold">Chuẩn Bonferroni</span>
              <div className="text-xl font-black text-emerald-400 mt-1">
                {currentSectorData.factors.filter(f => f.is_bonferroni_sig).length}
              </div>
            </div>
          </div>
        </div>

        {/* AI Executive Quick Take Sắc màu (2/3) */}
        <div className="lg:col-span-2 color-card p-6 sm:p-8 rounded-3xl relative overflow-hidden bg-gradient-to-br from-[#1A1138] via-[#101A33] to-[#0B1020] border border-purple-500/30">
          <div className="absolute top-0 right-0 p-8 opacity-15 pointer-events-none">
            <BrainCircuit className="w-40 h-40 text-purple-400" />
          </div>

          <div className="flex items-center space-x-2 text-cyan-300 text-xs font-bold uppercase tracking-wider mb-3">
            <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span>AI QUANTITATIVE TAKE · NHẬN ĐỊNH ĐỊNH LƯỢNG NGÀNH {currentSectorData.label.toUpperCase()}</span>
          </div>

          <h3 className="text-xl font-extrabold text-white mb-4">
            Đặc trưng tương quan tài chính và động lực giá cổ phiếu
          </h3>

          <div className="space-y-3.5 text-xs text-gray-200 leading-relaxed">
            <div className="flex items-start space-x-3 p-3 rounded-2xl bg-white/5 border border-white/10">
              <span className="w-6 h-6 rounded-xl bg-gradient-to-tr from-emerald-400 to-teal-500 text-black flex items-center justify-center shrink-0 font-black shadow-md">1</span>
              <p>
                <strong className="text-white">Nhân tố dẫn dắt mạnh nhất: </strong>
                Chỉ báo <span className="text-cyan-300 font-bold">{currentSectorData.factors[0]?.factor}</span> đạt hệ số tương quan Spearman <span className="font-mono text-emerald-300 font-black px-1.5 py-0.5 rounded bg-emerald-500/20">{currentSectorData.factors[0]?.correlation_percent}</span> ({currentSectorData.factors[0]?.direction}).
              </p>
            </div>

            <div className="flex items-start space-x-3 p-3 rounded-2xl bg-white/5 border border-white/10">
              <span className="w-6 h-6 rounded-xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-black flex items-center justify-center shrink-0 font-black shadow-md">2</span>
              <p>
                <strong className="text-white">Kiểm soát rủi ro Bonferroni: </strong>
                Có <span className="text-emerald-300 font-black font-mono">{currentSectorData.factors.filter(f => f.is_bonferroni_sig).length}</span> nhân tố vượt qua ngưỡng kiểm định khắt khe nhất (threshold α = {currentSectorData.factors[0]?.bonferroni_threshold || "0.0025"}).
              </p>
            </div>

            <div className="flex items-start space-x-3 p-3 rounded-2xl bg-white/5 border border-white/10">
              <span className="w-6 h-6 rounded-xl bg-gradient-to-tr from-amber-400 to-orange-500 text-black flex items-center justify-center shrink-0 font-black shadow-md">3</span>
              <p>
                <strong className="text-white">Khuyến nghị chiến lược đầu tư: </strong>
                Nên xây dựng bộ lọc đa nhân tố kết hợp giữa chỉ số tăng trưởng và hiệu quả sử dụng vốn để tối ưu hóa tỷ lệ Sharpe của danh mục ngành.
              </p>
            </div>
          </div>
        </div>

      </div>

      {/* Chart: Top 15 Factors Correlation Sắc màu */}
      <div className="color-card p-6 sm:p-8 rounded-3xl card-glow-cyan">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-lg font-bold text-white">Biểu đồ Tương quan Spearman (Top 15 Nhân tố)</h3>
            <p className="text-xs text-gray-400 mt-1">
              Thanh xanh ngọc (+) thể hiện đồng biến với giá · Thanh đỏ hồng (-) thể hiện nghịch biến
            </p>
          </div>
          <div className="flex items-center space-x-4 text-xs font-mono font-bold">
            <span className="flex items-center space-x-1.5 text-emerald-400 px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30">
              <span className="w-2.5 h-2.5 rounded bg-emerald-400"></span>
              <span>Đồng biến (+)</span>
            </span>
            <span className="flex items-center space-x-1.5 text-rose-400 px-2.5 py-1 rounded-lg bg-rose-500/15 border border-rose-500/30">
              <span className="w-2.5 h-2.5 rounded bg-rose-500"></span>
              <span>Nghịch biến (-)</span>
            </span>
          </div>
        </div>

        <div className="w-full h-84">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart
              data={chartFactors}
              margin={{ top: 20, right: 30, left: 20, bottom: 65 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#22304E" vertical={false} />
              <XAxis
                dataKey="name"
                angle={-35}
                textAnchor="end"
                interval={0}
                stroke="#CBD5E1"
                fontSize={11}
              />
              <YAxis
                stroke="#94A3B8"
                fontSize={11}
                unit="%"
                domain={[-100, 100]}
              />
              <ReferenceLine y={0} stroke="#475569" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0E1528",
                  borderColor: "#334155",
                  borderRadius: "14px",
                  color: "#F8FAFC",
                  fontSize: "12px",
                  boxShadow: "0 10px 30px -5px rgba(0,0,0,0.7)"
                }}
                formatter={(val: number, name: string, props: any) => [
                  `${val > 0 ? "+" : ""}${val}% (p = ${props.payload.p_value})`,
                  props.payload.fullName
                ]}
              />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {chartFactors.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.value >= 0 ? "#10B981" : "#F43F5E"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Comprehensive Factor Table Sắc màu */}
      <div className="color-card p-6 sm:p-8 rounded-3xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="font-extrabold text-white text-base">Toàn bộ Bảng Nhân tố Ngành {currentSectorData.label}</h3>
            <p className="text-xs text-gray-400 mt-1">
              Hiển thị {filteredFactors.length} / {currentSectorData.factors.length} chỉ báo tài chính
            </p>
          </div>

          {/* Search & Filter pills */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Tìm tên chỉ báo..."
                value={searchFactor}
                onChange={(e) => setSearchFactor(e.target.value)}
                className="pl-8 pr-3 py-1.5 bg-[#090D1C] border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 w-44 font-sans"
              />
            </div>

            <div className="flex items-center space-x-1 bg-[#090D1C] p-1 rounded-xl border border-white/10">
              <button
                onClick={() => setFilterMode("all")}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  filterMode === "all" ? "bg-white/15 text-white shadow-sm" : "text-gray-400 hover:text-white"
                }`}
              >
                Tất cả
              </button>
              <button
                onClick={() => setFilterMode("sig")}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  filterMode === "sig" ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20" : "text-gray-400 hover:text-white"
                }`}
              >
                p &lt; 0.05
              </button>
              <button
                onClick={() => setFilterMode("bonf")}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  filterMode === "bonf" ? "bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md shadow-emerald-500/20" : "text-gray-400 hover:text-white"
                }`}
              >
                Bonferroni
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#090D1C]/90 text-gray-300 font-bold uppercase tracking-wider border-b border-gray-800">
              <tr>
                <th className="py-3 px-3 text-center">Hạng</th>
                <th className="py-3 px-3">Chỉ báo tài chính</th>
                <th className="py-3 px-3">Phân loại</th>
                <th className="py-3 px-3 text-right">Tương quan</th>
                <th className="py-3 px-3">Chiều hướng</th>
                <th className="py-3 px-3">Mức độ</th>
                <th className="py-3 px-3 text-right">p-value</th>
                <th className="py-3 px-3 text-center">Kiểm định Bonferroni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/80 font-mono">
              {filteredFactors.map((f) => (
                <tr key={f.rank} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-3 text-center text-cyan-400 font-bold">
                    #{f.rank}
                  </td>
                  <td className="py-3 px-3 font-sans font-bold text-white">
                    {f.factor}
                  </td>
                  <td className="py-3 px-3 font-sans">
                    <span className="px-2 py-0.5 rounded-md bg-purple-500/15 text-purple-300 border border-purple-500/30 text-[11px] font-semibold">
                      {f.category}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right font-black">
                    <span className={f.correlation_value > 0 ? "text-emerald-400" : f.correlation_value < 0 ? "text-rose-400" : "text-gray-400"}>
                      {f.correlation_percent}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-sans">
                    <span className={`inline-flex items-center space-x-1 font-semibold ${f.direction === "Đồng biến" ? "text-emerald-400" : "text-rose-400"}`}>
                      {f.direction === "Đồng biến" ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                      <span>{f.direction}</span>
                    </span>
                  </td>
                  <td className="py-3 px-3 font-sans text-gray-300">
                    {f.strength}
                  </td>
                  <td className="py-3 px-3 text-right text-gray-300">
                    {f.p_value}
                  </td>
                  <td className="py-3 px-3 text-center font-sans">
                    {f.is_bonferroni_sig ? (
                      <span className="inline-flex items-center space-x-1 px-3 py-0.5 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-[10px] font-extrabold shadow-md shadow-emerald-500/20">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>ĐẠT CHUẨN</span>
                      </span>
                    ) : f.is_significant ? (
                      <span className="inline-block px-2.5 py-0.5 rounded-full bg-blue-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-bold">
                        p &lt; 0.05
                      </span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
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
