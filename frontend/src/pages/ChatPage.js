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
  const [scrollRequestKey, setScrollRequestKey] = useState(0);
  const requestScrollToBottom = () => {
    setScrollRequestKey(prev => prev + 1);
  };

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
    if (isChatLoading) {
      return;
    }
    chatApi
      .getMessages(activeConversationId)
      .then(setMessages)
      .catch(err => setError(err.message));
  }, [activeConversationId, isChatLoading, isLoggedIn]);

  const handleNewConversation = async () => {
    const conversation = await chatApi.createConversation('New conversation');
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

    const requestId = Date.now();
    const fileNames = files.map(file => file.name);
    const optimisticContent = fileNames.length
      ? `${content}\n\nAttachments: ${fileNames.join(', ')}`
      : content;
    const optimisticUserMessage = {
      id: `local-user-${requestId}`,
      role: 'user',
      content: optimisticContent,
      attachments: fileNames.map((name, index) => ({
        id: `local-file-${index}`,
        original_name: name,
        size: files[index].size,
      })),
    };
    const optimisticAssistantMessage = {
      id: `local-assistant-${requestId}`,
      role: 'assistant',
      content: '',
      attachments: [],
      sources: [],
      used_chunks: [],
      is_rag_answer: false,
      rag_score: null,
    };
    let streamingAssistantId = optimisticAssistantMessage.id;

    setMessages(prev => [...prev, optimisticUserMessage, optimisticAssistantMessage]);
    requestScrollToBottom();

    try {
      const uploadedAttachments = [];
      for (const file of files) {
        const attachment = await chatApi.uploadFile({
          conversationId: activeConversationId,
          file,
        });
        uploadedAttachments.push(attachment);
      }

      await chatApi.sendMessageStream({
        conversationId: activeConversationId,
        content,
        attachmentIds: uploadedAttachments.map(attachment => attachment.id),
        onEvent: (event) => {
          if (event?.type === 'start') {
            streamingAssistantId = event.assistant_message.id;
            setActiveConversationId(event.conversation.id);
            setMessages(prev => {
              const preserved = prev.filter(message => (
                message.id !== optimisticUserMessage.id
                && message.id !== optimisticAssistantMessage.id
                && message.id !== event.user_message.id
                && message.id !== event.assistant_message.id
              ));
              return [...preserved, event.user_message, event.assistant_message];
            });
            requestScrollToBottom();
            return;
          }

          if (event?.type === 'delta') {
            setMessages(prev => {
              const assistantExists = prev.some(message => message.id === streamingAssistantId);
              if (!assistantExists) {
                return [
                  ...prev,
                  { ...optimisticAssistantMessage, id: streamingAssistantId, content: event.delta || '' },
                ];
              }
              return prev.map(message => (
                message.id === streamingAssistantId
                  ? { ...message, content: `${message.content || ''}${event.delta || ''}` }
                  : message
              ));
            });
            requestScrollToBottom();
            return;
          }

          if (event?.type === 'done') {
            setActiveConversationId(event.conversation.id);
            setMessages(prev => prev.map(message => (
              message.id === streamingAssistantId
                ? event.assistant_message
                : message
            )));
            setConversations(prev => {
              const withoutCurrent = prev.filter(item => item.id !== event.conversation.id);
              return [event.conversation, ...withoutCurrent];
            });
            requestScrollToBottom();
          }
        },
      });
    } catch (err) {
      setMessages(prev => prev.filter(message => (
        message.id !== optimisticUserMessage.id && message.id !== optimisticAssistantMessage.id
      )));
      setError(err.message || 'Failed to send message');
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
        conversationId={activeConversationId}
        scrollRequestKey={scrollRequestKey}
        forceStickToBottom={isChatLoading}
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
