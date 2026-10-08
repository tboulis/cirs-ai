import { ChatInputProps } from "../../types";
import { useTranslation } from "react-i18next";
import { Send } from "lucide-react";

export const ChatInput = ({
  input,
  setInput,
  handleKeyPress,
  handleSendMessage,
  sendMessageMutation,
  selectedModel,
  inputRef,
}: ChatInputProps) => {
  const { t } = useTranslation();
  return (
    <div className="border-t border-secondary-200 bg-white p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex space-x-3">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t("chat.placeholder")}
              className="input resize-none"
              rows={1}
              style={{
                minHeight: "44px",
                maxHeight: "120px",
                resize: "none",
              }}
              disabled={sendMessageMutation.isLoading}
            />
          </div>

          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || sendMessageMutation.isLoading}
            className="btn-primary px-4 py-2 h-11"
          >
            {sendMessageMutation.isLoading ? (
              <div className="spinner"></div>
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        <div className="flex items-center justify-between mt-2 text-xs text-secondary-500">
          <span>{t("chat.pressEnter")}</span>
          <span>
            {t("model")}: {selectedModel}
          </span>
        </div>
      </div>
    </div>
  );
};
