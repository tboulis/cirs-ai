import { useTranslation } from "react-i18next";

export const Loader = () => {
  const { t } = useTranslation();
  return (
    <div className="text-center py-8">
      <div className="spinner mx-auto mb-2"></div>
      <p className="text-secondary-500">{t("chat.loadingConversation")}</p>
    </div>
  );
};
