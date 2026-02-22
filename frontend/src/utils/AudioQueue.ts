
export class AudioQueue {
    private queue: string[] = []; // Base64 audio strings
    private isPlaying: boolean = false;
    private currentAudio: HTMLAudioElement | null = null;
    private audioContext: AudioContext | null = null;
    private analyser: AnalyserNode | null = null;
    private sourceNode: MediaElementAudioSourceNode | null = null;
    private onPlaybackStateChange?: (isPlaying: boolean) => void;

    constructor(onPlaybackStateChange?: (isPlaying: boolean) => void) {
        this.onPlaybackStateChange = onPlaybackStateChange;
    }

    // Add audio chunk to queue
    enqueue(base64Audio: string) {
        // Initialize AudioContext on first interaction if not present
        this.initAudioContext();
        this.queue.push(base64Audio);
        this.playNext();
    }

    private initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
        }
    }

    // Play the next chunk in the queue
    private playNext() {
        if (this.isPlaying) return; // Prevent concurrent playback
        if (this.queue.length === 0) {
            this.isPlaying = false;
            if (this.onPlaybackStateChange) {
                this.onPlaybackStateChange(false);
            }
            return;
        }

        const base64Audio = this.queue.shift();
        if (!base64Audio) return;

        this.isPlaying = true;
        if (this.onPlaybackStateChange) {
            this.onPlaybackStateChange(true);
        }

        this.currentAudio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
        this.currentAudio.crossOrigin = "anonymous";

        // Connect to analyser if initialized
        if (this.audioContext && this.analyser) {
            // Need to create a new source node for the new audio element
            this.sourceNode = this.audioContext.createMediaElementSource(this.currentAudio);
            this.sourceNode.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
        }

        this.currentAudio.onended = () => {
            this.isPlaying = false;
            this.currentAudio = null;
            this.playNext(); // Try to play the next one
        };

        this.currentAudio.onerror = (e) => {
            console.error('Audio playback error', e);
            this.isPlaying = false;
            this.currentAudio = null;
            this.playNext(); // Skip error and try next
        };

        // Attempt to play
        this.currentAudio.play().catch(e => {
            console.error('Failed to play audio:', e);
            if (this.sourceNode) {
                this.sourceNode.disconnect();
                this.sourceNode = null;
            }
            this.isPlaying = false;
            this.currentAudio = null;
            this.playNext();
        });
    }

    // Clear queue and stop current playback
    clear() {
        this.queue = [];
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
        if (this.sourceNode) {
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }
        this.isPlaying = false;
        if (this.onPlaybackStateChange) {
            this.onPlaybackStateChange(false);
        }
    }

    getIsPlaying() {
        return this.isPlaying;
    }

    // Get current frequency data for visualizer
    getByteFrequencyData(): Uint8Array | null {
        if (!this.analyser || !this.isPlaying) return null;
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);
        return dataArray;
    }
}
