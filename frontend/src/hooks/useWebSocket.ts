import { useState, useEffect, useRef, useCallback } from 'react';
import type { ConnectionStatus } from '../types';
import { useLiveStore } from '../store/useLiveStore';
import { AudioQueue } from '../utils/AudioQueue';
import { v4 as uuidv4 } from 'uuid'; // need uuid for unique messages

interface UseWebSocketOptions {
    roomId: string;
    personaId: string;
}

export function useWebSocket({ roomId, personaId }: UseWebSocketOptions) {
    const [status, setStatus] = useState<ConnectionStatus>('Disconnected');
    const wsRef = useRef<WebSocket | null>(null);

    // Track bot typing state
    const isReceivingBotMessage = useRef(false);

    // Track own sent messages to deduplicate server echoes
    const sentMessagesRef = useRef<string[]>([]);

    // Zustand Store Actions
    const addMessage = useLiveStore(state => state.addMessage);
    const updateBotReply = useLiveStore(state => state.updateBotReply);
    const setStreamerState = useLiveStore(state => state.setStreamerState);

    // Audio Queue instance
    const audioQueueRef = useRef<AudioQueue | null>(null);

    // Initialize AudioQueue once
    useEffect(() => {
        audioQueueRef.current = new AudioQueue((isPlaying) => {
            if (isPlaying) {
                setStreamerState('Speaking');
            } else {
                // If it stopped playing, and we are not currently receiving a response, go to Idle
                if (!isReceivingBotMessage.current) {
                    setStreamerState('Idle');
                } else {
                    setStreamerState('Thinking');
                }
            }
        });
        // Save to global store for visualizer access
        useLiveStore.getState().setAudioQueue(audioQueueRef.current);

        return () => {
            if (audioQueueRef.current) {
                audioQueueRef.current.clear();
            }
        };
    }, [setStreamerState]);

    const connect = useCallback(() => {
        if (!roomId) return;

        // Auto generate client_id if needed, or backend relies on connection itself. 
        // Wait, backend URL is `/ws/rooms/{room_id}?persona_id={persona_id}` according to test html
        const wsUrl = `ws://localhost:8000/ws/rooms/${roomId}?persona_id=${personaId}`;

        if (wsRef.current) {
            wsRef.current.close();
        }

        setStatus('Connecting');
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setStatus('Connected');
            addMessage({
                id: uuidv4(),
                role: 'system',
                content: `已连接房间 [${roomId}] 🎉`,
                timestamp: new Date()
            });
        };

        ws.onclose = () => {
            setStatus('Disconnected');
            // basic reconnect could be added here with setTimeout
        };

        ws.onerror = (error) => {
            setStatus('Error');
            console.error("WebSocket error:", error);
        };

        ws.onmessage = (event) => {
            const msg: string = event.data;

            // 1. Other User message format: [USER:message]
            if (msg.startsWith('[USER:') && msg.endsWith(']')) {
                const userMsg = msg.substring(6, msg.length - 1);

                // Deduplicate if this is our own message echoing back
                const sentIndex = sentMessagesRef.current.indexOf(userMsg);
                if (sentIndex !== -1) {
                    // Remove from tracking to prevent false deduplication later
                    sentMessagesRef.current.splice(sentIndex, 1);
                    return; // Ignore the echo
                }

                addMessage({
                    id: uuidv4(),
                    role: 'other-user',
                    content: userMsg,
                    timestamp: new Date()
                });
                return;
            }

            // 2. Audio chunks format: [AUDIO:base64...]
            if (msg.startsWith('[AUDIO:')) {
                const base64Audio = msg.substring(7, msg.length - 1);
                if (audioQueueRef.current) {
                    audioQueueRef.current.enqueue(base64Audio);
                }
                return;
            }

            // 3. End of transmission format: [EOF]
            if (msg === '[EOF]') {
                isReceivingBotMessage.current = false;
                // If audio queue is not playing, set idle. If it is playing, AudioQueue handles state
                if (audioQueueRef.current && !audioQueueRef.current.getIsPlaying()) {
                    setStreamerState('Idle');
                }
                return;
            }

            // 4. Streamer Text Reply
            if (!isReceivingBotMessage.current) {
                // First chunk of Bot's reply
                isReceivingBotMessage.current = true;
                addMessage({
                    id: uuidv4(),
                    role: 'model',
                    content: msg,
                    timestamp: new Date()
                });
                // Also update state to Thinking, unless already Speaking due to rapid audio response
                if (audioQueueRef.current && !audioQueueRef.current.getIsPlaying()) {
                    setStreamerState('Thinking');
                }
            } else {
                // Subsequent chunk
                updateBotReply(msg);
            }
        };
    }, [roomId, personaId, addMessage, updateBotReply, setStreamerState]);

    useEffect(() => {
        // Remove auto-connect on mount
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);


    const sendMessage = useCallback((text: string) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && text.trim()) {
            addMessage({
                id: uuidv4(),
                role: 'user',
                content: text,
                timestamp: new Date()
            });
            // Track what we sent so we can filter out the server echo
            sentMessagesRef.current.push(text);
            wsRef.current.send(text);
        }
    }, [addMessage]);

    return {
        status,
        sendMessage,
        reconnect: connect
    };
}
