import { useState } from 'react';
import { ChatBox } from './components/ChatBox';
import { StreamerDisplay } from './components/StreamerDisplay';
import { ControlPanel } from './components/ControlPanel';
import { useWebSocket } from './hooks/useWebSocket';
import { useLiveStore } from './store/useLiveStore';

function App() {
  const [roomId, setRoomId] = useState('star');
  const [personaId, setPersonaId] = useState('bot_star');
  const { status, sendMessage, reconnect } = useWebSocket({ roomId, personaId });
  const clearMessages = useLiveStore(state => state.clearMessages);

  const handleConnect = () => {
    // Attempting to connect
    clearMessages();
    reconnect();
  };

  const handleDisconnect = () => {
    // Just reload page to disconnect is easiest way without complex teardown for now, 
    // or we could add a `disconnect` method to useWebSocket hook. For this demo, we'll reload.
    window.location.reload();
  };

  return (
    <div className="flex h-screen w-full bg-gradient-to-br from-gray-950 via-gray-900 to-black text-gray-100 p-6 gap-6 font-sans">

      {/* 顶部简易配置区（仅用于测试，正式可隐藏） */}
      <div className="fixed top-4 left-6 z-[999] flex gap-4 opacity-50 hover:opacity-100 transition-opacity bg-gray-900/80 p-3 rounded-2xl backdrop-blur-md border border-gray-700 shadow-xl">
        <select
          value={personaId}
          onChange={e => setPersonaId(e.target.value)}
          className="bg-gray-800 text-sm border-gray-600 rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        >
          <option value="bot_star">bot_star (星瞳)</option>
          <option value="bot_tech">bot_tech (极客老王)</option>
        </select>
        <input
          type="text"
          value={roomId}
          onChange={e => setRoomId(e.target.value)}
          placeholder="Room ID"
          className="w-24 bg-gray-800 text-sm border-gray-600 rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-none text-center"
        />
      </div>

      {/* 左侧：主播展示区 & 控制台 */}
      <div className="flex-1 flex flex-col relative h-full">
        {/* React component for Display */}
        <StreamerDisplay personaId={personaId} />

        {/* React component for Control */}
        <ControlPanel
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          status={status}
        />
      </div>

      {/* 右侧：弹幕交互区 */}
      <ChatBox onSendMessage={sendMessage} status={status} personaId={personaId} />

    </div>
  );
}

export default App;