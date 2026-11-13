"use client";

import React from "react";
import { 
  BarChart3, 
  Layers, 
  Search, 
  Bot, 
  Sparkles, 
  KeyRound, 
  Activity,
  Globe2,
  Zap,
  SlidersHorizontal,
  PieChart
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenSettings: () => void;
}

export default function Navbar({ activeTab, setActiveTab, onOpenSettings }: NavbarProps) {
  const navItems = [
    { 
      id: "overview", 
      label: "Tổng quan 10 ngành", 
      icon: BarChart3, 
      activeGradient: "from-cyan-500 via-teal-500 to-emerald-500",
      activeShadow: "shadow-cyan-500/25" 
    },
    { 
      id: "sector", 
      label: "Chi tiết ngành", 
      icon: Layers, 
      activeGradient: "from-purple-500 via-indigo-500 to-blue-500",
      activeShadow: "shadow-purple-500/25" 
    },
    { 
      id: "ticker", 
      label: "Tra cứu & So sánh", 
      icon: Search, 
      activeGradient: "from-emerald-500 via-teal-500 to-cyan-500",
      activeShadow: "shadow-emerald-500/25" 
    },
    { 
      id: "screener", 
      label: "Bộ lọc Screener", 
      icon: SlidersHorizontal, 
      badge: "HOT",
      activeGradient: "from-amber-500 via-orange-500 to-rose-500",
      activeShadow: "shadow-amber-500/25" 
    },
    { 
      id: "portfolio", 
      label: "Mô phỏng Danh mục", 
      icon: PieChart, 
      badge: "SIM",
      activeGradient: "from-blue-500 via-cyan-500 to-teal-500",
      activeShadow: "shadow-blue-500/25" 
    },
    { 
      id: "chat", 
      label: "AI Copilot Pro", 
      icon: Bot, 
      badge: "Llama 3.3",
      activeGradient: "from-pink-500 via-purple-500 to-indigo-500",
      activeShadow: "shadow-pink-500/25" 
    },
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-2xl bg-[#070913]/90 border-b border-white/10 transition-all w-full">
      <div className="w-full px-4 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between h-16 sm:h-20">
          
          {/* Brand Logo với Gradient Đa sắc */}
          <div 
            className="flex items-center space-x-3.5 cursor-pointer group"
            onClick={() => setActiveTab("overview")}
          >
            <div className="relative">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-cyan-400 via-purple-500 to-pink-500 p-[2px] shadow-lg shadow-purple-500/30 group-hover:shadow-cyan-500/50 group-hover:scale-105 transition-all duration-300">
                <div className="w-full h-full bg-[#080D1F] rounded-[14px] flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-cyan-300 group-hover:rotate-12 transition-transform duration-300" />
                </div>
              </div>
              <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-[#070913] flex items-center justify-center shadow-md shadow-emerald-500/50">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span>
              </span>
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <span className="font-black text-xl text-white tracking-tight bg-gradient-to-r from-cyan-300 via-purple-200 to-pink-300 bg-clip-text text-transparent">
                  VNSTOCK
                </span>
                <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-lg bg-gradient-to-r from-pink-500/20 via-purple-500/20 to-cyan-500/20 text-pink-300 border border-pink-500/30 uppercase tracking-wider shadow-sm">
                  QUANT AI
                </span>
              </div>
              <p className="text-[11px] text-gray-300 tracking-wide flex items-center space-x-1.5 mt-0.5 font-medium">
                <Activity className="w-3.5 h-3.5 text-teal-400" />
                <span>Financial Factor Engine · 2018–2024</span>
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs với hiệu ứng Gradient đa sắc */}
          <nav className="hidden lg:flex items-center space-x-1.5 bg-[#0F172E]/90 p-1.5 rounded-2xl border border-white/10 shadow-2xl">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`relative flex items-center space-x-2.5 px-4 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                    isActive
                      ? `bg-gradient-to-r ${item.activeGradient} text-white shadow-lg ${item.activeShadow} scale-[1.02]`
                      : "text-gray-300 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-gray-400"}`} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="text-[9px] px-1.5 py-0.2 bg-black/40 text-pink-200 rounded-md font-bold border border-pink-400/40">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Action Controls */}
          <div className="flex items-center space-x-3">
            <button
              onClick={onOpenSettings}
              className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-gray-900 to-[#121A30] hover:border-amber-500/50 text-gray-200 hover:text-white border border-white/10 transition-all text-xs font-semibold shadow-md group"
              title="Cấu hình Groq API Key cá nhân"
            >
              <KeyRound className="w-4 h-4 text-amber-400 group-hover:rotate-45 transition-transform" />
              <span className="hidden sm:inline">API Config</span>
            </button>

            <div className="hidden sm:flex items-center space-x-2 text-xs font-bold px-3.5 py-2 rounded-xl bg-gradient-to-r from-emerald-500/15 via-teal-500/15 to-cyan-500/15 border border-emerald-500/30 text-emerald-300 shadow-md shadow-emerald-500/10">
              <Zap className="w-3.5 h-3.5 text-emerald-400 animate-bounce" />
              <span>Vercel Edge 24/7</span>
            </div>
          </div>

        </div>

        {/* Mobile Nav Tabs */}
        <div className="lg:hidden flex items-center justify-around py-2.5 border-t border-white/10">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex flex-col items-center py-1.5 px-3 rounded-xl text-[11px] font-bold transition-all ${
                  isActive 
                    ? `text-white bg-gradient-to-r ${item.activeGradient} shadow-md` 
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <Icon className="w-4 h-4 mb-1" />
                <span>{item.label.split(" ")[0]}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
