import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import { useLiveStore } from '../store/useLiveStore';

interface ChatBoxProps {
    onSendMessage: (text: string) => void;
    status: string;
    personaId: string;
}

export function ChatBox({ onSendMessage, status, personaId }: ChatBoxProps) {
    const [inputText, setInputText] = useState('');
    const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
    const [lastSendTime, setLastSendTime] = useState(0);
    const [isCooldown, setIsCooldown] = useState(false);
    const messages = useLiveStore(state => state.messages);
    const chatContainerRef = useRef<HTMLDivElement>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (isScrolledToBottom) {
            chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isScrolledToBottom]);

    const handleScroll = () => {
        if (!chatContainerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
        // Check if we are within 20px of the bottom
        const atBottom = scrollHeight - scrollTop - clientHeight < 20;
        setIsScrolledToBottom(atBottom);
    };

    const handleSend = () => {
        const now = Date.now();
        if (now - lastSendTime < 2000) {
            setIsCooldown(true);
            setTimeout(() => setIsCooldown(false), 2000 - (now - lastSendTime));
            return;
        }

        if (inputText.trim()) {
            onSendMessage(inputText);
            setInputText('');
            setLastSendTime(now);
            setIsScrolledToBottom(true); // Force scroll to bottom on our own send
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    };

    return (
        <div className="w-96 bg-gray-800 rounded-2xl border border-gray-700 flex flex-col">
            {/* 顶部标题 */}
            <div className={`p-4 border-b border-gray-700 flex justify-between items-center ${personaId === 'bot_tech' ? 'bg-cyan-900/30' : 'bg-gray-900/50'} rounded-t-2xl transition-colors duration-500`}>
                <h2 className="font-bold text-lg text-white">
                    {personaId === 'bot_tech' ? '👨‍💻 老王的直播间' : '🌟 星瞳的直播间'}
                </h2>
                <span className={`flex items-center gap-2 text-sm font-medium ${status === 'Connected' ? 'text-green-400' : status === 'Connecting' ? 'text-yellow-400' : 'text-red-400'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${status === 'Connected' ? 'bg-green-400 animate-pulse shadow-[0_0_8px_rgba(74,222,128,0.5)]' : status === 'Connecting' ? 'bg-yellow-400' : 'bg-red-400'}`}></span>
                    {status === 'Connected' ? '已连接' : status === 'Connecting' ? '连接中...' : '已断开'}
                </span>
            </div>

            {/* 弹幕列表区 */}
            <div
                ref={chatContainerRef}
                onScroll={handleScroll}
                className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-transparent relative"
            >
                {messages.map((msg) => {
                    const isBot = msg.role === 'model';
                    const isSelf = msg.role === 'user';
                    const isSystem = msg.role === 'system';

                    if (isSystem) {
                        return (
                            <div key={msg.id} className="text-center text-xs text-gray-400 italic my-2 select-none">
                                {msg.content}
                            </div>
                        )
                    }

                    return (
                        <div
                            key={msg.id}
                            className={`px-3 py-2 rounded-xl text-[14px] leading-relaxed break-words hover:bg-gray-700/30 transition-colors w-full ${isBot ? 'bg-gray-700/20' : ''}`}
                        >
                            <span className={`inline-block font-bold mr-2 align-top ${isBot
                                    ? (personaId === 'bot_tech' ? 'text-cyan-400' : 'text-pink-400')
                                    : isSelf ? 'text-blue-400' : 'text-purple-400'
                                }`}>
                                {isBot && <span className="mr-1">{personaId === 'bot_tech' ? '👨‍💻' : '✨'}</span>}
                                {isBot ? (personaId === 'bot_tech' ? '极客老王' : '星瞳') : (isSelf ? '我' : '观众')}
                                <span className="text-gray-500 ml-1 opacity-50 px-0.5">:</span>
                            </span>
                            <span className={`${isBot ? 'text-gray-100 font-medium' : 'text-gray-300'}`}>
                                {msg.content}
                            </span>
                        </div>
                    );
                })}
                <div ref={chatEndRef} />
            </div>

            {/* 底部输入框 */}
            <div className="p-4 border-t border-gray-700 bg-gray-800/80 rounded-b-2xl flex gap-2 backdrop-blur-md">
                <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={isCooldown ? "发送太频繁，请稍后再试..." : "发送弹幕跟主播互动..."}
                    disabled={status !== 'Connected' || isCooldown}
                    className={`flex-1 bg-gray-900 border ${isCooldown ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500' : 'border-gray-600 focus:border-blue-500 focus:ring-blue-500'} rounded-xl px-4 py-2.5 
                     focus:outline-none focus:ring-1 
                     text-[15px] text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all`}
                />
                <button
                    onClick={handleSend}
                    disabled={status !== 'Connected' || !inputText.trim() || isCooldown}
                    className={`${isCooldown ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-500'} disabled:bg-gray-700 disabled:text-gray-500 text-white p-3 rounded-xl transition-all flex items-center justify-center shadow-lg ${isCooldown ? 'shadow-red-900/20' : 'shadow-blue-900/20'} active:scale-95`}
                >
                    <Send size={18} className={inputText.trim() && status === 'Connected' ? 'translate-x-0.5 -translate-y-0.5 transition-transform' : ''} />
                </button>
            </div>
        </div>
    );
}
