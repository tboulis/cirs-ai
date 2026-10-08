import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Menu, Settings, Upload, MessageCircle, Globe } from "lucide-react";
import { useTranslation } from "react-i18next";
import Sidebar from "../Sidebar/Sidebar";
import ChatInterface from "../Chat/ChatInterface";
import { chatApi, systemApi } from "../../services/api";
import { Conversation, ModelInfo } from "../../types";
import { toast } from "react-hot-toast";

const ChatLayout: React.FC = () => {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { t, i18n } = useTranslation();
  const toggleLanguage = () => {
    const newLang = i18n.language.startsWith("en") ? "el" : "en";
    i18n.changeLanguage(newLang);
  };

  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentConversation, setCurrentConversation] = useState<
    Conversation | undefined
  >();
  const [selectedModel, setSelectedModel] = useState<string>("gpt-3.5-turbo");

  // Fetch conversations
  const {
    data: conversations = [],
    isLoading: conversationsLoading,
    refetch: refetchConversations,
  } = useQuery(["conversations"], () => chatApi.getConversations(), {
    onError: (error) => {
      console.error("Error fetching conversations:", error);
      toast.error("Failed to load conversations");
    },
  });

  // Fetch available models
  const { data: modelsData } = useQuery(
    ["models"],
    () => systemApi.getModels(),
    {
      onSuccess: (data) => {
        if (data.default_model) {
          setSelectedModel(data.default_model);
        }
      },
      onError: (error) => {
        console.error("Error fetching models:", error);
      },
    }
  );

  // Set current conversation based on URL parameter
  useEffect(() => {
    if (conversationId) {
      // Attempt to find the conversation in the fetched list (may not be there yet)
      const conversation = conversations.find(
        (c) => c.id === parseInt(conversationId)
      );

      // Only update if we actually found it. This prevents briefly resetting to
      // an old state (or undefined) while we wait for the refetch to include
      // the brand-new conversation we just created.
      if (conversation) {
        setCurrentConversation(conversation);
      }
    } else {
      setCurrentConversation(undefined);
    }
  }, [conversationId, conversations]);

  const handleNewConversation = () => {
    setCurrentConversation(undefined);
    navigate("/chat");
  };

  const handleConversationSelect = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    navigate(`/chat/${conversation.id}`);
  };

  const handleConversationDelete = async (conversationId: number) => {
    try {
      await chatApi.deleteConversation(conversationId);
      toast.success("Conversation deleted");
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(undefined);
        navigate("/chat");
      }
      refetchConversations();
    } catch (error) {
      console.error("Error deleting conversation:", error);
      toast.error("Failed to delete conversation");
    }
  };

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <div className="flex h-screen bg-secondary-50">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={handleSidebarToggle}
        conversations={conversations}
        onConversationSelect={handleConversationSelect}
        currentConversationId={currentConversation?.id}
        onNewConversation={handleNewConversation}
        isLoading={conversationsLoading}
        onConversationDelete={handleConversationDelete}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-secondary-200 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={handleSidebarToggle}
                className="btn-ghost p-2"
                aria-label="Toggle sidebar"
              >
                <Menu className="w-5 h-5" />
              </button>

              <div className="flex items-center space-x-2">
                <MessageCircle className="w-6 h-6 text-primary-600" />
                <h1 className="text-xl font-semibold text-secondary-900">
                  {currentConversation?.title || "CIRS-AI Assistant"}
                </h1>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {/* Model selector */}
              {modelsData && (
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="input text-sm py-1 px-2 w-40"
                >
                  {modelsData.models.map((model: ModelInfo) => (
                    <option key={model.name} value={model.name}>
                      {model.name} ({model.provider})
                    </option>
                  ))}
                </select>
              )}

              {/* Action buttons */}
              <button
                onClick={toggleLanguage}
                className="btn-ghost p-2"
                title={t(`lang.${i18n.language}`)}
              >
                <Globe className="w-5 h-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Chat interface */}
        <div className="flex-1 overflow-hidden">
          <ChatInterface
            conversation={currentConversation}
            selectedModel={selectedModel}
            onConversationUpdate={(updatedConversation) => {
              setCurrentConversation(updatedConversation);
              // Keep URL in sync with the newly created / updated conversation
              if (updatedConversation?.id) {
                navigate(`/chat/${updatedConversation.id}`);
              }
              refetchConversations();
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatLayout;
