"use client";

import React, { useState } from "react";
import { KeyRound, X, Check, ExternalLink } from "lucide-react";

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  userApiKey: string;
  onSaveApiKey: (key: string) => void;
}

export default function ApiKeyModal({
  isOpen,
  onClose,
  userApiKey,
  onSaveApiKey,
}: ApiKeyModalProps) {
  const [keyInput, setKeyInput] = useState(userApiKey);
  const [saved, setSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveApiKey(keyInput.trim());
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-2xl relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 absolute top-4 right-4 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <KeyRound className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Cấu hình GROQ API Key</h3>
            <p className="text-xs text-gray-400">Tùy chọn API Key cá nhân để không bị giới hạn tốc độ</p>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-4">
          <p className="text-xs text-gray-300 leading-relaxed">
            Mặc định, hệ thống đã tích hợp sẵn API Key của hệ thống. Nếu bạn muốn sử dụng API Key riêng của mình từ Groq Cloud (miễn phí), bạn có thể dán vào bên dưới.
          </p>

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Groq API Key (gsk_...)
            </label>
            <input
              type="password"
              placeholder="gsk_..."
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              className="w-full px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-xl text-sm text-white font-mono placeholder-gray-600 focus:outline-none focus:border-teal-500 transition-colors"
            />
          </div>

          <a
            href="https://console.groq.com/keys"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-1.5 text-xs text-teal-400 hover:text-teal-300 transition-colors"
          >
            <span>Lấy Groq API Key miễn phí tại console.groq.com</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-gray-800">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white transition-colors"
            >
              Đóng
            </button>
            <button
              onClick={handleSave}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-400 hover:to-emerald-500 text-white shadow-md shadow-teal-500/20 transition-all"
            >
              {saved ? (
                <>
                  <Check className="w-4 h-4 text-white" />
                  <span>Đã lưu!</span>
                </>
              ) : (
                <span>Lưu cấu hình</span>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
