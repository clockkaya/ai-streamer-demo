export type Role = 'user' | 'model' | 'other-user' | 'system';

export interface ChatMessage {
  id: string; // Used as the React key
  role: Role;
  content: string;
  timestamp: Date;
}

export type StreamerState = 'Idle' | 'Thinking' | 'Speaking';

export type ConnectionStatus = 'Connecting' | 'Connected' | 'Error' | 'Disconnected';

export interface RoomInfo {
  roomId: string;
  personaId: string;
  onlineCount: number;
}
