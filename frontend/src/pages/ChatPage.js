import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import './ChatPage.css';

function ChatPage() {
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <div className="chat-page">
      <AnimatePresence>
        {sidebarVisible && (
          <Sidebar
            isLoggedIn={isLoggedIn}
            onLogout={() => setIsLoggedIn(false)}
          />
        )}
      </AnimatePresence>
      <ChatArea
        sidebarVisible={sidebarVisible}
        onToggleSidebar={() => setSidebarVisible(!sidebarVisible)}
        isLoggedIn={isLoggedIn}
      />
    </div>
  );
}

export default ChatPage;
