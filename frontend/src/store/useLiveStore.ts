import { create } from 'zustand';
import type { ChatMessage, StreamerState } from '../types';
import type { AudioQueue } from '../utils/AudioQueue';

interface LiveStore {
    // 状态
    messages: ChatMessage[];
    streamerState: StreamerState;
    onlineCount: number;
    audioQueue: AudioQueue | null;

    // Actions
    addMessage: (msg: ChatMessage) => void;
    updateBotReply: (chunk: string) => void;
    setStreamerState: (state: StreamerState) => void;
    setOnlineCount: (count: number) => void;
    setAudioQueue: (queue: AudioQueue) => void;
    clearMessages: () => void;
}

export const useLiveStore = create<LiveStore>((set) => ({
    messages: [],
    streamerState: 'Idle',
    onlineCount: 1,
    audioQueue: null,

    addMessage: (msg) =>
        set((state) => ({ messages: [...state.messages, msg] })),

    updateBotReply: (chunk) =>
        set((state) => {
            const messages = [...state.messages];
            if (messages.length === 0) return { messages };

            const lastMsg = messages[messages.length - 1];
            if (lastMsg.role === 'model') {
                const updatedMsg = { ...lastMsg, content: lastMsg.content + chunk };
                messages[messages.length - 1] = updatedMsg;
            }
            return { messages };
        }),

    setStreamerState: (streamerState) => set({ streamerState }),

    setOnlineCount: (onlineCount) => set({ onlineCount }),

    setAudioQueue: (audioQueue) => set({ audioQueue }),

    clearMessages: () => set({ messages: [] }),
}));
