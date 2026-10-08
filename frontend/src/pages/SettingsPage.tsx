import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Database, Info, ArrowLeft, Upload } from "lucide-react";
import { systemApi } from "../services/api";

const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("models");

  // Fetch system health
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: systemApi.getHealth,
  });

  // Fetch available models
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ["models"],
    queryFn: systemApi.getModels,
  });

  const tabs = [
    { id: "models", label: "Models", icon: Bot },
    { id: "database", label: "Database", icon: Database },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <div className="min-h-screen bg-secondary-50">
      {/* Top navigation bar */}
      <header className="bg-white border-b border-secondary-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => window.history.back()}
              className="btn-ghost p-2"
              title="Back"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>

            <Info className="w-6 h-6 text-primary-600" />
            <h1 className="text-lg font-semibold text-secondary-900">
              Settings
            </h1>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => (window.location.href = "/documents")}
              className="btn-ghost p-2"
              title="Documents"
            >
              <Upload className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">Settings</h1>
          <p className="text-secondary-600 mt-2">
            Configure your CIRS-AI assistant preferences and system settings
          </p>
        </div>

        <div className="flex space-x-8">
          {/* Sidebar */}
          <div className="w-64 space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 text-left rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? "bg-primary-100 text-primary-900 border border-primary-200"
                      : "text-secondary-700 hover:bg-secondary-100"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Content */}
          <div className="flex-1">
            {activeTab === "models" && (
              <ModelsSettings
                modelsData={modelsData}
                isLoading={modelsLoading}
              />
            )}
            {activeTab === "database" && (
              <DatabaseSettings health={health} isLoading={healthLoading} />
            )}
            {activeTab === "about" && <AboutSettings />}
          </div>
        </div>
      </div>
    </div>
  );
};

// Models settings component
const ModelsSettings: React.FC<{ modelsData: any; isLoading: boolean }> = ({
  modelsData,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="card p-8">
        <div className="spinner mx-auto mb-4"></div>
        <p className="text-center text-secondary-500">Loading models...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-secondary-900 mb-4">
          Available Models
        </h2>

        {modelsData?.models?.length > 0 ? (
          <div className="space-y-4">
            {modelsData.models.map((model: any) => (
              <div
                key={model.name}
                className="border border-secondary-200 rounded-lg p-4 hover:bg-secondary-50"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-secondary-900">
                      {model.name}
                    </h3>
                    <p className="text-sm text-secondary-600">
                      {model.description}
                    </p>
                    <div className="flex items-center space-x-4 mt-2 text-xs text-secondary-500">
                      <span>Provider: {model.provider}</span>
                      <span>
                        Context: {model.context_length?.toLocaleString()} tokens
                      </span>
                      {model.cost_per_token > 0 && (
                        <span>Cost: ${model.cost_per_token}/token</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        model.status === "available"
                          ? "bg-success-100 text-success-700"
                          : "bg-warning-100 text-warning-700"
                      }`}
                    >
                      {model.status || "available"}
                    </span>

                    {model.name === modelsData.default_model && (
                      <span className="px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded-full">
                        Default
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-secondary-500">No models available</p>
        )}
      </div>
    </div>
  );
};

// Database settings component
const DatabaseSettings: React.FC<{ health: any; isLoading: boolean }> = ({
  health,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="card p-8">
        <div className="spinner mx-auto mb-4"></div>
        <p className="text-center text-secondary-500">
          Loading system status...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-secondary-900 mb-4">
          System Status
        </h2>

        {health && (
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-secondary-200">
              <span className="text-secondary-700">Overall Status</span>
              <span
                className={`px-3 py-1 text-sm font-medium rounded-full ${
                  health.status === "healthy"
                    ? "bg-success-100 text-success-700"
                    : "bg-error-100 text-error-700"
                }`}
              >
                {health.status}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-secondary-200">
              <span className="text-secondary-700">Database</span>
              <span
                className={`px-3 py-1 text-sm font-medium rounded-full ${
                  health.database_status === "healthy"
                    ? "bg-success-100 text-success-700"
                    : "bg-error-100 text-error-700"
                }`}
              >
                {health.database_status}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-secondary-200">
              <span className="text-secondary-700">Version</span>
              <span className="text-secondary-900 font-medium">
                {health.version}
              </span>
            </div>

            <div className="flex items-center justify-between py-2">
              <span className="text-secondary-700">Last Check</span>
              <span className="text-secondary-900 font-medium">
                {new Date(health.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// About settings component
const AboutSettings: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-secondary-900 mb-4">
          About CIRS-AI
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-secondary-900 mb-2">
              Critical Infrastructure Resilience Support
            </h3>
            <p className="text-secondary-600 text-sm">
              CIRS-AI is an intelligent assistant designed to help organizations
              understand and implement best practices for protecting critical
              infrastructure systems.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-secondary-900 mb-2">
              Version Information
            </h3>
            <div className="text-sm text-secondary-600 space-y-1">
              <div>Version: 1.0.0</div>
              <div>Build: 2024.01.01</div>
              <div>Frontend: React + TypeScript</div>
              <div>Backend: Python + FastAPI</div>
            </div>
          </div>

          <div>
            <h3 className="font-medium text-secondary-900 mb-2">Features</h3>
            <ul className="text-sm text-secondary-600 space-y-1 list-disc list-inside">
              <li>Multi-model LLM support (OpenAI, Mistral, LLaMA)</li>
              <li>Document upload and semantic search</li>
              <li>Conversation history and management</li>
              <li>Real-time chat interface</li>
              <li>Context-aware responses using uploaded documents</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold text-secondary-900 mb-4">
          Support
        </h3>
        <p className="text-secondary-600 text-sm mb-4">
          For technical support, feature requests, or bug reports, please
          contact the development team.
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex items-center space-x-2">
            <span className="text-secondary-500">GitHub:</span>
            <a
              href="https://github.com/tboulis"
              className="text-primary-600 hover:underline"
            >
              github.com/tboulis
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
