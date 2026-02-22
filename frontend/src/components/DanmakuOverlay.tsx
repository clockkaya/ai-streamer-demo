import { useEffect, useState, useRef } from 'react';
import { useLiveStore } from '../store/useLiveStore';

interface DanmakuItem {
    id: string;
    text: string;
    top: number;
    duration: number;
}

export function DanmakuOverlay() {
    const messages = useLiveStore(state => state.messages);
    const [danmakus, setDanmakus] = useState<DanmakuItem[]>([]);
    const lastMessageCount = useRef(0);

    useEffect(() => {
        if (messages.length > lastMessageCount.current) {
            // New messages arrived
            const newMessages = messages.slice(lastMessageCount.current);

            const newDanmakus = newMessages
                .filter(msg => msg.role === 'other-user' || msg.role === 'user')
                .map(msg => ({
                    id: msg.id + '-' + Date.now(), // Ensure uniqueness even if same msg rendered twice for some reason
                    text: msg.content,
                    top: Math.random() * 80 + 5, // Random height from 5% to 85%
                    duration: Math.random() * 4 + 6, // Random duration between 6s and 10s
                }));

            if (newDanmakus.length > 0) {
                setDanmakus(prev => [...prev, ...newDanmakus]);

                // Clean up after duration + buffer
                newDanmakus.forEach(d => {
                    setTimeout(() => {
                        setDanmakus(current => current.filter(item => item.id !== d.id));
                    }, d.duration * 1000 + 1000);
                });
            }
        }
        lastMessageCount.current = messages.length;
    }, [messages]);

    return (
        <div className="absolute inset-0 pointer-events-none z-40 overflow-hidden rounded-3xl">
            {danmakus.map(danmaku => (
                <div
                    key={danmaku.id}
                    className="absolute whitespace-nowrap text-white font-bold text-lg px-3 py-1 bg-black/30 backdrop-blur-sm rounded-full shadow-[0_2px_8px_rgba(0,0,0,0.5)] border border-white/10 opacity-90"
                    style={{
                        top: `${danmaku.top}%`,
                        right: '-100%', // Start off-screen right
                        animation: `flyLeft ${danmaku.duration}s linear forwards`,
                        textShadow: '1px 1px 2px black, -1px -1px 2px black, 1px -1px 2px black, -1px 1px 2px black'
                    }}
                >
                    {danmaku.text}
                </div>
            ))}
            <style>{`
        @keyframes flyLeft {
          from { transform: translateX(0); }
          to { transform: translateX(-250vw); } /* Ensure it flies completely off screen left */
        }
      `}</style>
        </div>
    );
}
