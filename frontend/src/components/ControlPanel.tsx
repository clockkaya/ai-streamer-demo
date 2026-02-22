import { useEffect, useRef, useState } from 'react';
import { Play, Square, Volume2, Mic, Settings } from 'lucide-react';
import { useLiveStore } from '../store/useLiveStore';

interface ControlPanelProps {
    onConnect: () => void;
    onDisconnect: () => void;
    status: string;
}

export function ControlPanel({ onConnect, onDisconnect, status }: ControlPanelProps) {
    const isConnected = status === 'Connected';
    const streamerState = useLiveStore(state => state.streamerState);
    const audioQueue = useLiveStore(state => state.audioQueue);
    const [volumeLevel, setVolumeLevel] = useState(0);
    const requestRef = useRef<number>(0);

    useEffect(() => {
        if (streamerState === 'Speaking' && audioQueue) {
            const updateVisualizer = () => {
                const data = audioQueue.getByteFrequencyData();
                if (data) {
                    // Calculate average volume from frequencies
                    let sum = 0;
                    for (let i = 0; i < data.length; i++) {
                        sum += data[i];
                    }
                    const avg = sum / data.length;
                    // Normalize to 0-100% (max byte value is 255)
                    const level = Math.min(100, (avg / 255) * 100 * 2.5); // 2.5 is a visual boost multiplier
                    setVolumeLevel(level);
                }
                requestRef.current = requestAnimationFrame(updateVisualizer);
            };
            requestRef.current = requestAnimationFrame(updateVisualizer);
        } else {
            setVolumeLevel(0);
            if (requestRef.current) {
                cancelAnimationFrame(requestRef.current);
            }
        }

        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [streamerState, audioQueue]);

    return (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-gray-900/90 backdrop-blur-xl px-8 py-4 rounded-3xl border border-gray-700/50 flex items-center gap-8 shadow-2xl transition-all hover:bg-gray-900 z-50">
            {/* 核心连接控制区 */}
            <div className="flex items-center gap-4">
                {!isConnected ? (
                    <button
                        onClick={onConnect}
                        className="flex items-center justify-center bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 hover:text-blue-300 p-3 rounded-xl transition-all group relative overflow-hidden"
                        title="开始直播连线"
                    >
                        <div className="absolute inset-0 bg-blue-400/10 scale-0 group-hover:scale-150 transition-transform duration-500 rounded-full"></div>
                        <Play size={24} className="relative z-10" />
                        <span className="ml-2 font-bold text-sm tracking-widest uppercase relative z-10">开始</span>
                    </button>
                ) : (
                    <button
                        onClick={onDisconnect}
                        className="flex items-center justify-center bg-red-600/20 text-red-400 hover:bg-red-600/30 hover:text-red-300 p-3 rounded-xl transition-all group relative overflow-hidden min-w-[100px]"
                        title="断开直播连线"
                    >
                        <div className="absolute inset-0 bg-red-400/10 scale-0 group-hover:scale-150 transition-transform duration-500 rounded-full"></div>
                        <Square size={24} className="relative z-10" />
                        <span className="ml-2 font-bold text-sm tracking-widest uppercase relative z-10">停止</span>
                    </button>
                )}
            </div>

            <div className="w-px h-8 bg-gray-700/80 rounded-full"></div>

            {/* 状态与指示器 */}
            <div className="flex items-center gap-4">
                <button className={`p-2 rounded-xl transition-all flex items-center justify-center ${streamerState === 'Speaking' ? 'text-green-400 bg-green-500/10 ring-1 ring-green-500/50' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
                    }`} title="麦克风状态">
                    <Mic size={20} />
                    {streamerState === 'Speaking' && (
                        <span className="absolute -top-1 -right-1 flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                        </span>
                    )}
                </button>

                <div className="flex items-center gap-3 bg-gray-800/50 px-4 py-2 rounded-xl border border-gray-700/30">
                    <Volume2 size={18} className="text-gray-400" />
                    {/* 真实的音频频谱可视化高度 */}
                    <div className="w-24 h-1.5 bg-gray-700/50 rounded-full overflow-hidden flex items-center">
                        <div
                            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-75 ease-linear"
                            style={{ width: `${volumeLevel}%` }}
                        ></div>
                    </div>
                </div>

                <button className="text-gray-500 hover:text-gray-300 p-2 rounded-xl hover:bg-gray-800 transition-colors" title="直播设置">
                    <Settings size={20} className="hover:rotate-90 transition-transform duration-500" />
                </button>
            </div>
        </div>
    );
}
