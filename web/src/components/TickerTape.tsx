"use client";

import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

interface TickerTapeProps {
  onSelectTicker?: (ticker: string) => void;
}

export default function TickerTape({ onSelectTicker }: TickerTapeProps) {
  const tickerItems = [
    { ticker: "VCB", name: "Vietcombank", price: "92.5", change: "+1.4%", up: true, pe: "14.2" },
    { ticker: "FPT", name: "FPT Corp", price: "138.2", change: "+2.8%", up: true, pe: "22.5" },
    { ticker: "TCB", name: "Techcombank", price: "24.8", change: "+1.9%", up: true, pe: "7.8" },
    { ticker: "VHM", name: "Vinhomes", price: "43.5", change: "-0.7%", up: false, pe: "6.9" },
    { ticker: "HPG", name: "Hòa Phát", price: "28.6", change: "+0.8%", up: true, pe: "11.4" },
    { ticker: "SSI", name: "Chứng khoán SSI", price: "32.1", change: "+2.1%", up: true, pe: "15.3" },
    { ticker: "DGC", name: "Hóa chất Đức Giang", price: "116.0", change: "+3.2%", up: true, pe: "13.8" },
    { ticker: "MWG", name: "Thế Giới Di Động", price: "68.5", change: "-1.2%", up: false, pe: "18.2" },
    { ticker: "GAS", name: "PV Gas", price: "79.2", change: "+0.5%", up: true, pe: "16.1" },
    { ticker: "VNM", name: "Vinamilk", price: "66.8", change: "+0.3%", up: true, pe: "14.9" },
    { ticker: "REE", name: "Cơ Điện Lạnh", price: "64.0", change: "+1.6%", up: true, pe: "9.7" },
    { ticker: "DHG", name: "Dược Hậu Giang", price: "112.5", change: "-0.4%", up: false, pe: "13.2" },
    { ticker: "GMD", name: "Gemadept", price: "82.4", change: "+2.4%", up: true, pe: "12.0" },
  ];

  // Nhân đôi để hiệu ứng marquee lặp vô tận mượt mà
  const displayList = [...tickerItems, ...tickerItems];

  return (
    <div className="w-full bg-[#0A0E1A]/95 border-b border-gray-800/80 overflow-hidden py-2 backdrop-blur-sm">
      <div className="flex items-center">
        {/* Label cố định bên trái */}
        <div className="hidden sm:flex items-center space-x-2 pl-4 pr-3 border-r border-gray-800 shrink-0 z-10 bg-[#0A0E1A]">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-[11px] font-bold text-gray-300 uppercase tracking-wider">THỊ TRƯỜNG</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono font-semibold">
            VN-INDEX: 1,285.6 (+9.2)
          </span>
        </div>

        {/* Marquee ticker list */}
        <div className="overflow-hidden flex-1 relative">
          <div className="animate-marquee flex items-center space-x-6 text-xs font-mono">
            {displayList.map((item, idx) => (
              <div
                key={idx}
                onClick={() => onSelectTicker && onSelectTicker(item.ticker)}
                className="flex items-center space-x-2.5 px-2.5 py-1 rounded-lg hover:bg-gray-800/60 cursor-pointer transition-colors group shrink-0"
              >
                <span className="font-bold text-white group-hover:text-teal-400 transition-colors">
                  {item.ticker}
                </span>
                <span className="text-gray-400 text-[11px]">{item.price}</span>
                <span
                  className={`inline-flex items-center space-x-0.5 font-semibold text-[11px] ${
                    item.up ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {item.up ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  <span>{item.change}</span>
                </span>
                <span className="text-[10px] text-gray-600 border border-gray-800 px-1 rounded">
                  P/E: {item.pe}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
