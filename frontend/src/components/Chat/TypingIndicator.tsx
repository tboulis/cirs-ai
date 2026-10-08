import { Bot } from "lucide-react";

export const TypingIndicator = () => {
  return (
    <div className="flex items-start space-x-3">
      <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
        <Bot className="w-5 h-5 text-white" />
      </div>
      <div className="message-assistant p-4 max-w-3xl">
        <div className="typing-indicator">
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
        </div>
      </div>
    </div>
  );
};
