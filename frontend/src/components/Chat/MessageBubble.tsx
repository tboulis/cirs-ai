import React from "react";
import { Bot, User, FileText, Clock, Zap } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Message } from "../../types";
import clsx from "clsx";
import { useDateFormatting } from "../../hooks/date-formatting";

interface MessageBubbleProps {
  message: Message;
  isLast?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === "user";

  const { distanceToNow } = useDateFormatting();

  return (
    <div
      className={clsx(
        "flex items-start space-x-3 animate-fade-in-up",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
          <Bot className="w-5 h-5 text-white" />
        </div>
      )}

      <div
        className={clsx(
          "p-4 max-w-3xl",
          isUser ? "message-user" : "message-assistant"
        )}
      >
        <div className="prose prose-sm max-w-none">
          {isUser ? (
            <p className="mb-0">{message.content}</p>
          ) : (
            <ReactMarkdown
              components={{
                code({ className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !match;
                  return !isInline ? (
                    <pre className="bg-gray-900 text-white p-4 rounded-lg overflow-x-auto">
                      <code className={className}>
                        {String(children).replace(/\n$/, "")}
                      </code>
                    </pre>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Message metadata */}
        <div className="flex items-center space-x-3 mt-2 text-xs text-secondary-400">
          <div className="flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>{distanceToNow(message.created_at)}</span>
          </div>

          {message.model_used && (
            <div className="flex items-center space-x-1">
              <Bot className="w-3 h-3" />
              <span>{message.model_used}</span>
            </div>
          )}

          {message.response_time && (
            <div className="flex items-center space-x-1">
              <Zap className="w-3 h-3" />
              <span>{(message.response_time * 1000).toFixed(0)}ms</span>
            </div>
          )}

          {message.tokens_used && (
            <div className="flex items-center space-x-1">
              <FileText className="w-3 h-3" />
              <span>{message.tokens_used} tokens</span>
            </div>
          )}
        </div>
      </div>

      {/* Sources list */}
      {message.sources && message.sources.length > 0 && (
        <div className="mt-3 text-xs text-secondary-500">
          <div className="font-bold">Sources: </div>
          {message.sources.map((s, idx) => {
            console.log(s);
            return (
              <span key={s.id}>
                [{s.id}] {s.document_title}
                {idx < (message.sources?.length || 0) - 1 && ", "}
              </span>
            );
          })}
        </div>
      )}

      {isUser && (
        <div className="w-8 h-8 bg-secondary-600 rounded-full flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
};
