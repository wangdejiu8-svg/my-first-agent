import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import { useAuth } from '../contexts/AuthContext';
import { chatApi } from '../services/chatApi';
import './ChatPage.css';

function ChatPage() {
  const { user, isLoggedIn, logout } = useAuth();
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState('');

  const loadConversations = useCallback(async () => {
    if (!isLoggedIn) {
      setConversations([]);
      setActiveConversationId(null);
      setMessages([]);
      return;
    }
    const data = await chatApi.getConversations();
    setConversations(data);
    if (!activeConversationId && data.length > 0) {
      setActiveConversationId(data[0].id);
    }
  }, [activeConversationId, isLoggedIn]);

  useEffect(() => {
    loadConversations().catch(err => setError(err.message));
  }, [loadConversations]);

  useEffect(() => {
    if (!activeConversationId || !isLoggedIn) {
      setMessages([]);
      return;
    }
    chatApi
      .getMessages(activeConversationId)
      .then(setMessages)
      .catch(err => setError(err.message));
  }, [activeConversationId, isLoggedIn]);

  const handleNewConversation = async () => {
    const conversation = await chatApi.createConversation('新对话');
    setConversations(prev => [conversation, ...prev]);
    setActiveConversationId(conversation.id);
    setMessages([]);
  };

  const handleDeleteConversation = async (conversationId) => {
    setError('');
    await chatApi.deleteConversation(conversationId);
    setConversations(prev => {
      const nextConversations = prev.filter(item => item.id !== conversationId);
      if (activeConversationId === conversationId) {
        const nextActive = nextConversations[0]?.id || null;
        setActiveConversationId(nextActive);
        if (!nextActive) {
          setMessages([]);
        }
      }
      return nextConversations;
    });
  };

  const handleSendMessage = async (content, files = []) => {
    setError('');
    setIsChatLoading(true);
    const fileNames = files.map(file => file.name);
    const optimisticContent = fileNames.length
      ? `${content}\n\n附件：${fileNames.join('、')}`
      : content;
    const optimisticUserMessage = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: optimisticContent,
      attachments: fileNames.map((name, index) => ({
        id: `local-file-${index}`,
        original_name: name,
        size: files[index].size,
      })),
    };
    setMessages(prev => [...prev, optimisticUserMessage]);
    try {
      const uploadedAttachments = [];
      for (const file of files) {
        const attachment = await chatApi.uploadFile({
          conversationId: activeConversationId,
          file,
        });
        uploadedAttachments.push(attachment);
      }
      const data = await chatApi.sendMessage({
        conversationId: activeConversationId,
        content,
        attachmentIds: uploadedAttachments.map(attachment => attachment.id),
      });
      setActiveConversationId(data.conversation.id);
      setMessages(prev => [
        ...prev.filter(message => message.id !== optimisticUserMessage.id),
        data.user_message,
        data.assistant_message,
      ]);
      setConversations(prev => {
        const withoutCurrent = prev.filter(item => item.id !== data.conversation.id);
        return [data.conversation, ...withoutCurrent];
      });
    } catch (err) {
      setMessages(prev => prev.filter(message => message.id !== optimisticUserMessage.id));
      setError(err.message || '发送失败');
      throw err;
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div className="chat-page">
      <AnimatePresence>
        {sidebarVisible && (
          <Sidebar
            user={user}
            isLoggedIn={isLoggedIn}
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={setActiveConversationId}
            onNewConversation={handleNewConversation}
            onDeleteConversation={handleDeleteConversation}
            onLogout={logout}
          />
        )}
      </AnimatePresence>
      <ChatArea
        sidebarVisible={sidebarVisible}
        onToggleSidebar={() => setSidebarVisible(!sidebarVisible)}
        isLoggedIn={isLoggedIn}
        messages={messages}
        error={error}
        isLoading={isChatLoading}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}

export default ChatPage;
