import { useLiveStore } from '../store/useLiveStore';
import { DanmakuOverlay } from './DanmakuOverlay';

export function StreamerDisplay({ personaId }: { personaId: string }) {
    const streamerState = useLiveStore(state => state.streamerState);

    // Based on state, determine visual feedback
    const getStatusColor = () => {
        switch (streamerState) {
            case 'Speaking': return 'ring-green-500 shadow-[0_0_30px_rgba(34,197,94,0.3)] bg-green-500/10';
            case 'Thinking': return 'ring-yellow-500 shadow-[0_0_30px_rgba(234,179,8,0.3)] bg-yellow-500/10 animate-pulse';
            case 'Idle':
            default: return 'ring-gray-700 bg-gray-800 border-gray-700';
        }
    };

    const getStatusText = () => {
        switch (streamerState) {
            case 'Speaking': return '正在讲话... 🎙️';
            case 'Thinking': return '思考中... 🤔';
            case 'Idle':
            default: return '待机中 💤';
        }
    };

    return (
        <div className="flex-1 bg-gray-900/80 rounded-3xl border border-gray-800 flex flex-col items-center justify-center relative overflow-hidden backdrop-blur-xl shadow-2xl">
            <DanmakuOverlay />
            {/* Background decoration */}
            <div className={`absolute top-[-20%] left-[-10%] w-[60%] h-[60%] ${personaId === 'bot_tech' ? 'bg-cyan-600/10' : 'bg-blue-600/10'} rounded-full blur-[100px] pointer-events-none transition-colors duration-1000`}></div>
            <div className={`absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] ${personaId === 'bot_tech' ? 'bg-emerald-600/10' : 'bg-purple-600/10'} rounded-full blur-[100px] pointer-events-none transition-colors duration-1000`}></div>

            {/* 虚拟主播画面区 */}
            <div className="flex flex-col items-center gap-6 z-10 w-full mb-20 animate-in fade-in zoom-in duration-500">
                {/* Live2D / 3D Avatar Placeholder */}
                <div className={`relative w-64 h-64 rounded-full flex items-center justify-center transition-all duration-500 ring-4 ring-offset-8 ring-offset-gray-900 border border-gray-700 overflow-hidden ${getStatusColor()}`}>

                    {/* Inner Avatar Graphic */}
                    <div className={`absolute inset-2 rounded-full border border-gray-600 flex items-center justify-center overflow-hidden transition-all duration-700 bg-gradient-to-b from-gray-700 to-gray-800 ${streamerState === 'Speaking' ? 'scale-105' : 'scale-100'}`}>
                        {streamerState === 'Speaking' ? (
                            <span className="text-7xl animate-bounce">🗣️</span>
                        ) : streamerState === 'Thinking' ? (
                            <span className="text-7xl animate-pulse">🤔</span>
                        ) : (
                            <span className="text-7xl relative top-5 opacity-80">{personaId === 'bot_tech' ? '👨‍💻' : '🌟'}</span>
                        )}
                    </div>

                    {/* Audio Waveform visualizer (Fake CSS) */}
                    {streamerState === 'Speaking' && (
                        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-1.5 h-8">
                            {[1, 2, 3, 4, 5, 6].map(i => (
                                <div key={i} className={`w-1.5 bg-green-400 rounded-full animate-pulse`}
                                    style={{
                                        height: `${Math.random() * 80 + 20}%`,
                                        animationDuration: `${Math.random() * 0.5 + 0.3}s`
                                    }}
                                ></div>
                            ))}
                        </div>
                    )}
                </div>

                <div className={`px-6 py-2 rounded-full backdrop-blur-md border border-gray-700/50 shadow-lg text-sm font-medium tracking-wide transition-colors ${streamerState === 'Speaking' ? 'bg-green-500/20 text-green-300' :
                    streamerState === 'Thinking' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-gray-800 text-gray-400'
                    }`}>
                    {getStatusText()}
                </div>
            </div>
        </div>
    );
}
