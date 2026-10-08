import { Bot } from "lucide-react";
import { useTranslation } from "react-i18next";

export const EmptyConversationMessage = () => {
  const { t } = useTranslation();

  return (
    <div className="text-center py-12">
      <Bot className="w-16 h-16 text-primary-600 mx-auto mb-4" />
      <h2 className="text-2xl font-semibold text-secondary-900 mb-2">
        {t("chat.welcomeTitle")}
      </h2>
      <p className="text-secondary-600 max-w-md mx-auto">
        {t("chat.welcomeSubtitle")}
      </p>
    </div>
  );
};
