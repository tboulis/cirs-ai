import React from "react";
import { Trash2, Calendar } from "lucide-react";
import { Conversation } from "../../types";
import clsx from "clsx";
import { useTranslation } from "react-i18next";

import { useDateFormatting } from "../../hooks/date-formatting";

type ConversationItemProps = {
  conversation: Conversation;
  onConversationSelect: (conversation: Conversation) => void;
  currentConversationId?: number;
  handleDeleteConversation: (
    e: React.MouseEvent,
    conversationId: number
  ) => void;
};

export const ConversationItem = ({
  conversation,
  onConversationSelect,
  currentConversationId,
  handleDeleteConversation,
}: ConversationItemProps) => {
  const { t } = useTranslation();
  const { distanceToNow } = useDateFormatting();

  return (
    <button
      key={conversation.id}
      onClick={() => onConversationSelect(conversation)}
      className={clsx(
        "w-full text-left p-3 rounded-lg border transition-colors group",
        currentConversationId === conversation.id
          ? "bg-primary-50 border-primary-200 text-primary-900"
          : "bg-white border-secondary-200 hover:bg-secondary-50 text-secondary-900"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium truncate">
            {conversation.title || t("sidebar.untitledConversation")}
          </h4>

          <div className="flex items-center space-x-2 mt-1">
            <Calendar className="w-3 h-3 text-secondary-400" />
            <span className="text-xs text-secondary-500">
              {distanceToNow(conversation.created_at)}
            </span>
          </div>

          <div className="text-xs text-secondary-400 mt-1">
            {t("sidebar.messages", {
              count: conversation.message_count,
            })}
          </div>
        </div>

        <span
          onClick={(e) => handleDeleteConversation(e, conversation.id)}
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-error-100 rounded"
          title={t("sidebar.deleteConversation")}
        >
          <Trash2 className="w-4 h-4 text-error-500" />
        </span>
      </div>
    </button>
  );
};
