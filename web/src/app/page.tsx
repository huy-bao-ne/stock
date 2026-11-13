"use client";

import React, { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import TickerTape from "@/components/TickerTape";
import OverviewTab from "@/components/OverviewTab";
import SectorTab from "@/components/SectorTab";
import TickerTab from "@/components/TickerTab";
import ScreenerTab from "@/components/ScreenerTab";
import PortfolioTab from "@/components/PortfolioTab";
import ChatbotTab from "@/components/ChatbotTab";
import ApiKeyModal from "@/components/ApiKeyModal";
import { Sparkles, Globe2, ShieldCheck, Cpu } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedSector, setSelectedSector] = useState("BANKING");
  const [activeTicker, setActiveTicker] = useState("VCB");
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [userApiKey, setUserApiKey] = useState("");

  useEffect(() => {
    try {
      const storedKey = localStorage.getItem("vnstock_groq_api_key");
      if (storedKey) setUserApiKey(storedKey);
    } catch (e) {
      // Ignore
    }
  }, []);

  const handleSaveApiKey = (key: string) => {
    setUserApiKey(key);
    try {
      if (key) {
        localStorage.setItem("vnstock_groq_api_key", key);
      } else {
        localStorage.removeItem("vnstock_groq_api_key");
      }
    } catch (e) {
      // Ignore
    }
  };

  const handleSelectSector = (sectorKey: string) => {
    setSelectedSector(sectorKey);
    setActiveTab("sector");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSelectTickerFromTape = (ticker: string) => {
    setActiveTicker(ticker);
    setActiveTab("ticker");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen flex flex-col aurora-bg bg-grid-tech relative text-slate-100 overflow-x-hidden">
      
      {/* Dynamic Ambient Neon Blobs */}
      <div className="fixed top-20 left-10 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -z-10 animate-pulse"></div>
      <div className="fixed top-40 right-10 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none -z-10 animate-pulse [animation-delay:2s]"></div>
      <div className="fixed bottom-20 left-1/3 w-96 h-96 bg-pink-500/10 rounded-full blur-3xl pointer-events-none -z-10"></div>

      {/* Navigation Bar Toàn màn hình */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Live Market Ticker Tape Toàn màn hình */}
      <TickerTape onSelectTicker={handleSelectTickerFromTape} />

      {/* Main Container Toàn Màn Hình (Fluid Full Width, không còn co cụm max-w-7xl) */}
      <main className="flex-1 w-full px-4 sm:px-8 lg:px-12 py-6 md:py-8 z-10">
        {activeTab === "overview" && (
          <OverviewTab onSelectSector={handleSelectSector} />
        )}

        {activeTab === "sector" && (
          <SectorTab
            selectedSector={selectedSector}
            onSelectSector={setSelectedSector}
          />
        )}

        {activeTab === "ticker" && (
          <TickerTab initialTicker={activeTicker} />
        )}

        {activeTab === "screener" && (
          <ScreenerTab onSelectTicker={handleSelectTickerFromTape} />
        )}

        {activeTab === "portfolio" && (
          <PortfolioTab />
        )}

        {activeTab === "chat" && (
          <ChatbotTab
            userApiKey={userApiKey}
            onOpenSettings={() => setIsSettingsOpen(true)}
          />
        )}
      </main>

      {/* API Key Modal */}
      <ApiKeyModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        userApiKey={userApiKey}
        onSaveApiKey={handleSaveApiKey}
      />

      {/* Footer Toàn màn hình */}
      <footer className="border-t border-white/10 bg-[#070913]/90 mt-12 py-8 text-xs text-gray-400">
        <div className="w-full px-4 sm:px-8 lg:px-12 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <span className="font-black text-white text-sm bg-gradient-to-r from-cyan-400 via-teal-300 to-pink-400 bg-clip-text text-transparent">
              VNSTOCK Factor Quant AI
            </span>
            <span className="text-gray-600">|</span>
            <span>10 Ngành Kinh tế (2018–2024)</span>
            <span className="text-gray-600">|</span>
            <span className="text-cyan-300 font-semibold">Spearman & Bonferroni Engine</span>
          </div>

          <div className="flex items-center space-x-4">
            <span className="flex items-center space-x-2 text-emerald-400 font-mono text-[11px] font-bold px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Next.js 14 Serverless · Ready for Vercel</span>
            </span>
          </div>
        </div>
      </footer>

    </div>
  );
}
