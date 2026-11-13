"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  Bot, 
  User, 
  Send, 
  RotateCcw, 
  Sparkles, 
  Copy, 
  Check, 
  Zap, 
  BookOpen, 
  Scale, 
  TrendingUp, 
  Cpu 
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatbotTabProps {
  userApiKey: string;
  onOpenSettings: () => void;
}

export default function ChatbotTab({ userApiKey, onOpenSettings }: ChatbotTabProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Ref cuộn NỘI BỘ container tin nhắn, KHÔNG chạm vào scroll của toàn bộ trang
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Load chat history
  useEffect(() => {
    try {
      const saved = localStorage.getItem("vnstock_ai_chat_history");
      if (saved) {
        setMessages(JSON.parse(saved));
      }
    } catch (e) {
      // Ignore
    }
  }, []);

  // Save chat history
  useEffect(() => {
    try {
      localStorage.setItem("vnstock_ai_chat_history", JSON.stringify(messages));
    } catch (e) {
      // Ignore
    }
  }, [messages]);

  // Cuộn NỘI BỘ container chat một cách êm ái, TUYỆT ĐỐI không làm tuột màn hình trang web
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages, loading]);

  // Analysis Presets với màu sắc riêng biệt
  const presets = [
    {
      title: "Nhân tố dẫn dắt thị trường",
      icon: TrendingUp,
      color: "from-cyan-500/25 to-blue-500/10 border-cyan-500/40 text-cyan-300",
      iconBg: "bg-cyan-500/20 text-cyan-300",
      desc: "Ngành nào có factor mạnh nhất sau Bonferroni?",
      prompt: "Dựa trên dữ liệu 10 ngành, ngành nào sở hữu nhân tố có độ tương quan mạnh nhất và vượt qua kiểm định Bonferroni? Phân tích ý nghĩa tài chính của nhân tố này."
    },
    {
      title: "So sánh đối đầu ngân hàng",
      icon: Scale,
      color: "from-purple-500/25 to-indigo-500/10 border-purple-500/40 text-purple-300",
      iconBg: "bg-purple-500/20 text-purple-300",
      desc: "So sánh hiệu quả tài chính VCB vs TCB",
      prompt: "So sánh toàn diện chỉ số ROA, ROE, Tăng trưởng và tỷ suất sinh lời cổ phiếu giữa VCB và TCB trong giai đoạn 2018–2024. Mã nào có chất lượng tài chính vượt trội hơn?"
    },
    {
      title: "Giải thích phương pháp Bonferroni",
      icon: BookOpen,
      color: "from-amber-500/25 to-orange-500/10 border-amber-500/40 text-amber-300",
      iconBg: "bg-amber-500/20 text-amber-300",
      desc: "Tại sao Bonferroni lại quan trọng?",
      prompt: "Giải thích tại sao trong nghiên cứu định lượng tài chính (Quantitative Finance), kiểm định Bonferroni Correction lại vô cùng quan trọng để chống bẫy false-positive?"
    },
    {
      title: "Khám phá nhóm Công nghệ",
      icon: Cpu,
      color: "from-emerald-500/25 to-teal-500/10 border-emerald-500/40 text-emerald-300",
      iconBg: "bg-emerald-500/20 text-emerald-300",
      desc: "Phân tích nhóm FPT, CMG, CTR",
      prompt: "Trong ngành Công nghệ (FPT, CMG, CTR, ELC, SGT), những chỉ số tài chính nào tương quan đồng biến mạnh nhất với giá cổ phiếu?"
    }
  ];

  const handleSend = async (questionText?: string) => {
    const q = (questionText || input).trim();
    if (!q || loading) return;

    const newMessages: Message[] = [...messages, { role: "user", content: q }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: newMessages,
          userApiKey: userApiKey || undefined,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Lỗi không xác định khi gọi AI");
      }

      setMessages([...newMessages, { role: "assistant", content: data.reply }]);
    } catch (err: any) {
      const errorMsg =
        err.message?.includes("rate") || err.message?.includes("429")
          ? "⏳ **Groq API đang bị giới hạn tần suất (Rate Limit).** Vui lòng đợi 30 giây rồi thử lại, hoặc nhập API Key cá nhân trong phần Cài đặt nhé!"
          : `⚠️ **Lỗi:** ${err.message || "Không thể kết nối đến máy chủ AI."}`;

      setMessages([...newMessages, { role: "assistant", content: errorMsg }]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    if (confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện không?")) {
      setMessages([]);
      localStorage.removeItem("vnstock_ai_chat_history");
    }
  };

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Render format
  const renderFormattedContent = (content: string) => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let tableBuffer: string[] = [];

    const flushTable = (keyPrefix: number) => {
      if (tableBuffer.length < 2) {
        tableBuffer.forEach((l, i) => elements.push(<p key={`${keyPrefix}-${i}`} className="mb-2">{l}</p>));
        tableBuffer = [];
        return;
      }

      const headerLine = tableBuffer[0];
      const headers = headerLine.split("|").map(h => h.trim()).filter(Boolean);
      const rows = tableBuffer.slice(2).map(r => r.split("|").map(c => c.trim()).filter(Boolean));

      elements.push(
        <div key={`table-${keyPrefix}`} className="overflow-x-auto my-4 rounded-2xl border border-cyan-500/30 bg-[#090E1D] shadow-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#141E38] text-cyan-300 font-bold uppercase tracking-wider">
              <tr>
                {headers.map((h, i) => (
                  <th key={i} className="py-3 px-3.5 border-b border-white/10">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 font-mono">
              {rows.map((row, rIdx) => (
                <tr key={rIdx} className="hover:bg-white/5 transition-colors">
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="py-2.5 px-3.5 text-gray-200">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableBuffer = [];
    };

    lines.forEach((line, idx) => {
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        tableBuffer.push(line.trim());
      } else {
        if (tableBuffer.length > 0) {
          flushTable(idx);
        }

        if (line.startsWith("### ")) {
          elements.push(<h4 key={idx} className="text-base font-bold text-white mt-4 mb-2">{line.replace("### ", "")}</h4>);
        } else if (line.startsWith("## ")) {
          elements.push(<h3 key={idx} className="text-lg font-bold text-cyan-300 mt-5 mb-2">{line.replace("## ", "")}</h3>);
        } else if (line.startsWith("# ")) {
          elements.push(<h2 key={idx} className="text-xl font-extrabold text-white mt-6 mb-3">{line.replace("# ", "")}</h2>);
        } else if (line.startsWith("- ") || line.startsWith("* ")) {
          elements.push(
            <li key={idx} className="ml-5 list-disc text-gray-200 mb-1 leading-relaxed">
              {formatInlineStyles(line.slice(2))}
            </li>
          );
        } else if (line.trim() === "") {
          elements.push(<div key={idx} className="h-2" />);
        } else {
          elements.push(
            <p key={idx} className="text-gray-200 leading-relaxed mb-2">
              {formatInlineStyles(line)}
            </p>
          );
        }
      }
    });

    if (tableBuffer.length > 0) {
      flushTable(lines.length);
    }

    return elements;
  };

  const formatInlineStyles = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} className="text-cyan-300 font-bold">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={i} className="px-1.5 py-0.5 rounded-md bg-purple-950/80 text-pink-300 text-xs font-mono border border-purple-500/30">{part.slice(1, -1)}</code>;
      }
      return part;
    });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-fadeIn w-full">
      
      {/* Left Sidebar: Analysis Presets Sắc màu (1/4) */}
      <div className="lg:col-span-1 space-y-4">
        <div className="color-card p-5 sm:p-6 rounded-3xl space-y-3 card-glow-purple">
          <div className="flex items-center space-x-2 text-cyan-300 text-xs font-bold uppercase tracking-wider">
            <Zap className="w-4 h-4 text-cyan-400 animate-bounce" />
            <span>KỊCH BẢN PHÂN TÍCH NHANH</span>
          </div>
          <p className="text-xs text-gray-300">
            Bấm chọn để nạp ngay câu hỏi định lượng chuyên sâu vào AI:
          </p>

          <div className="space-y-2.5 pt-2">
            {presets.map((preset, idx) => {
              const Icon = preset.icon;
              return (
                <button
                  key={idx}
                  onClick={() => handleSend(preset.prompt)}
                  className={`w-full p-3.5 rounded-2xl bg-gradient-to-r ${preset.color} border text-left transition-all duration-300 hover:scale-[1.02] shadow-md group flex items-start space-x-3`}
                >
                  <div className={`p-2.5 rounded-xl ${preset.iconBg} shrink-0 mt-0.5 shadow-sm`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-extrabold text-white group-hover:text-cyan-300 transition-colors">
                      {preset.title}
                    </div>
                    <div className="text-[11px] text-gray-300 mt-0.5 line-clamp-1">
                      {preset.desc}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* AI Spec Card */}
        <div className="color-card p-5 rounded-3xl space-y-2 bg-gradient-to-br from-[#1C1138] to-[#0A0F1F] border border-purple-500/30">
          <span className="text-[10px] font-bold text-purple-300 uppercase tracking-wider">HẠ TẦNG AI COPILOT</span>
          <div className="text-sm font-bold text-white flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Llama 3.3 70B & Local Engine</span>
          </div>
          <p className="text-[11px] text-gray-300 leading-relaxed">
            Hỗ trợ phân tích song song: Groq LPU siêu tốc hoặc Động cơ Phân tích Nội bộ chống sập.
          </p>
        </div>
      </div>

      {/* Main Chat Interface (3/4) — Chiều cao linh hoạt và cuộn NỘI BỘ */}
      <div className="lg:col-span-3 flex flex-col h-[calc(100vh-210px)] min-h-[640px] color-card rounded-3xl overflow-hidden card-glow-cyan shadow-2xl">
        
        {/* Chat Room Header */}
        <div className="p-4 sm:p-5 bg-gradient-to-r from-[#0C152B] via-[#141233] to-[#0C152B] border-b border-white/10 flex items-center justify-between shrink-0 backdrop-blur-md">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-400 via-purple-500 to-pink-500 p-[2px] shadow-lg shadow-purple-500/25">
              <div className="w-full h-full bg-[#080D1A] rounded-[14px] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-cyan-300" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-extrabold text-white text-base">VNSTOCK AI Copilot</h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-mono font-bold shadow-sm">
                  ACTIVE
                </span>
              </div>
              <p className="text-xs text-gray-300">Trợ lý phân tích định lượng & định giá doanh nghiệp</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {messages.length > 0 && (
              <button
                onClick={handleReset}
                title="Xóa lịch sử hội thoại"
                className="p-2 sm:px-3 sm:py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-gray-200 hover:text-white transition-all text-xs flex items-center space-x-1.5 border border-white/10"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Làm mới</span>
              </button>
            )}
          </div>
        </div>

        {/* Message Container — Cuộn NỘI BỘ qua ref messagesContainerRef */}
        <div 
          ref={messagesContainerRef} 
          className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6"
        >
          
          {/* Empty State */}
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-10 space-y-4 animate-fadeIn">
              <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-cyan-500 via-purple-500 to-pink-500 p-0.5 shadow-2xl">
                <div className="w-full h-full bg-[#080D1F] rounded-[22px] flex items-center justify-center">
                  <Bot className="w-8 h-8 text-cyan-300" />
                </div>
              </div>
              <h3 className="text-2xl font-black text-white">Bạn cần phân tích chỉ số nào hôm nay?</h3>
              <p className="text-xs text-gray-300 leading-relaxed">
                Hỏi bất kỳ điều gì về hệ số tương quan Spearman, kiểm định Bonferroni, so sánh các chỉ tiêu BCTC hoặc đánh giá xu hướng tài chính của 50 mã cổ phiếu lớn nhất.
              </p>
            </div>
          )}

          {/* Chat Messages */}
          {messages.map((msg, idx) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={idx}
                className={`flex items-start space-x-3 ${isUser ? "justify-end" : "justify-start"} animate-fadeIn`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-purple-600 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-md shadow-cyan-500/20">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`relative max-w-[85%] sm:max-w-[80%] p-4 sm:p-5 rounded-2xl text-xs sm:text-sm ${
                    isUser
                      ? "bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 text-white rounded-tr-none shadow-xl shadow-cyan-500/20"
                      : "bg-[#0E162B]/95 border border-white/10 text-gray-100 rounded-tl-none shadow-lg"
                  }`}
                >
                  {!isUser && (
                    <button
                      onClick={() => handleCopy(msg.content, idx)}
                      className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-gray-300 hover:text-white transition-colors"
                      title="Sao chép câu trả lời"
                    >
                      {copiedIndex === idx ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}

                  <div className="prose prose-invert max-w-none">
                    {isUser ? msg.content : renderFormattedContent(msg.content)}
                  </div>
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-500 to-pink-600 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-md shadow-purple-500/20">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading Indicator */}
          {loading && (
            <div className="flex items-start space-x-3 animate-fadeIn">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="p-4 rounded-2xl bg-[#0E162B] border border-white/10 rounded-tl-none flex items-center space-x-2.5">
                <span className="text-xs text-cyan-300 font-semibold">AI đang tính toán dữ liệu định lượng...</span>
                <div className="flex space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-bounce [animation-delay:0.4s]"></span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar Sắc màu cố định ở đáy container chat */}
        <div className="p-4 bg-gradient-to-r from-[#0C152B] via-[#10142A] to-[#0C152B] border-t border-white/10 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              placeholder="Đặt câu hỏi về nhân tố, chỉ số tài chính, so sánh mã cổ phiếu..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              className="flex-1 bg-[#070B17] border border-cyan-500/30 rounded-2xl px-5 py-3.5 text-xs sm:text-sm text-white placeholder-gray-400 focus:outline-none focus:border-cyan-400 transition-colors disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3.5 bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 hover:scale-105 text-white rounded-2xl font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-xl shadow-purple-500/30 shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="flex items-center justify-between text-[10px] text-gray-400 mt-2 px-1">
            <span className="font-medium">Powered by Llama 3.3 70B & VNSTOCK Local Engine</span>
            <span className="text-cyan-400 font-bold">Inference latency ~0.3s</span>
          </div>
        </div>

      </div>

    </div>
  );
}
