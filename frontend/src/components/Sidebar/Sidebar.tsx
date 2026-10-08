import React from "react";
import {
  Plus,
  MessageSquare,
  ChevronLeft,
  FileText,
  Settings,
  LogOut,
} from "lucide-react";
import { Conversation } from "../../types";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { ConversationItem } from "./ConversationItem";
import { authApi } from "../../services/api";
import { useNavigate } from "react-router-dom";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  conversations: Conversation[];
  onConversationSelect: (conversation: Conversation) => void;
  currentConversationId?: number;
  onNewConversation: () => void;
  onConversationDelete: (conversationId: number) => void;
  isLoading?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onToggle,
  conversations,
  onConversationSelect,
  currentConversationId,
  onNewConversation,
  onConversationDelete,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleDeleteConversation = (
    e: React.MouseEvent,
    conversationId: number
  ) => {
    e.stopPropagation();
    onConversationDelete(conversationId);
  };

  return (
    <>
      {/* Sidebar overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <div
        className={clsx(
          "fixed inset-y-0 left-0 z-50 bg-white border-r border-secondary-200 transform transition-all duration-300 ease-in-out overflow-hidden lg:relative",
          isOpen
            ? "translate-x-0 w-80 lg:translate-x-0 lg:w-80"
            : "-translate-x-full w-80 lg:translate-x-0 lg:w-0"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-secondary-200">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-lg font-semibold text-secondary-900">
                CIRS-Agent
              </h2>
            </div>

            <button
              onClick={onToggle}
              className="btn-ghost p-1 lg:hidden"
              aria-label="Close sidebar"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>

          {/* New conversation button */}
          <div className="p-4">
            <button
              onClick={onNewConversation}
              className="btn-primary w-full flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>{t("newConversation")}</span>
            </button>
          </div>

          {/* Navigation */}
          <nav className="px-4 pb-4">
            <div className="space-y-1">
              <a
                href="/chat"
                className="flex items-center space-x-3 px-3 py-2 text-sm font-medium text-secondary-700 rounded-lg hover:bg-secondary-100"
              >
                <MessageSquare className="w-5 h-5" />
                <span>{t("nav.chat")}</span>
              </a>

              <a
                href="/documents"
                className="flex items-center space-x-3 px-3 py-2 text-sm font-medium text-secondary-700 rounded-lg hover:bg-secondary-100"
              >
                <FileText className="w-5 h-5" />
                <span>{t("nav.documents")}</span>
              </a>

              <a
                href="/settings"
                className="flex items-center space-x-3 px-3 py-2 text-sm font-medium text-secondary-700 rounded-lg hover:bg-secondary-100"
                title={t("nav.settings")}
              >
                <Settings className="w-5 h-5" />
                <span>{t("nav.settings")}</span>
              </a>
            </div>
          </nav>

          {/* Conversation history */}
          <div className="flex-1 overflow-y-auto">
            <div className="px-4 py-2">
              <h3 className="text-xs font-semibold text-secondary-500 uppercase tracking-wide">
                {t("sidebar.recent")}
              </h3>
            </div>

            <div className="px-4 pb-4">
              {isLoading ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-16 bg-secondary-200 rounded-lg"></div>
                    </div>
                  ))}
                </div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-8">
                  <MessageSquare className="w-12 h-12 text-secondary-300 mx-auto mb-3" />
                  <p className="text-sm text-secondary-500">
                    {t("sidebar.noConversations")}
                  </p>
                  <p className="text-xs text-secondary-400 mt-1">
                    {t("sidebar.startPrompt")}
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {conversations.map((conversation) => (
                    <ConversationItem
                      key={conversation.id}
                      conversation={conversation}
                      onConversationSelect={onConversationSelect}
                      currentConversationId={currentConversationId}
                      handleDeleteConversation={handleDeleteConversation}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-secondary-200">
            {/* Logout control */}
            <button
              className={clsx(
                "w-full flex items-center justify-center btn-danger",
                !isOpen && "px-2 py-2"
              )}
              title="Logout"
              onClick={() => {
                authApi.logout();
                navigate("/login", { replace: true });
              }}
            >
              <LogOut className="w-5 h-5" />
              <span className={clsx("ml-2", !isOpen && "hidden")}>Logout</span>
            </button>

            {/* Divider */}
            <div className="my-3 border-t border-secondary-200" />

            {/* Version */}
            <div className="text-xs text-secondary-500 text-center">
              CIRS-Agent v1.0.0
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
