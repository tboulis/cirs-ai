import React, { useEffect, useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import ChatLayout from "./components/Layout/ChatLayout";
import DocumentsPage from "./pages/DocumentsPage";
import SettingsPage from "./pages/SettingsPage";
import LoginPage from "./pages/LoginPage";
import { authApi } from "./services/api";
import "./index.css";

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  const [loggedIn, setLoggedIn] = useState<boolean>(authApi.isAuthenticated());

  // Listen for authentication changes
  useEffect(() => {
    const handler = () => setLoggedIn(authApi.isAuthenticated());
    window.addEventListener("auth-changed", handler);
    return () => window.removeEventListener("auth-changed", handler);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                loggedIn ? <ChatLayout /> : <Navigate to="/login" replace />
              }
            />
            <Route
              path="/chat"
              element={
                loggedIn ? <ChatLayout /> : <Navigate to="/login" replace />
              }
            />
            <Route
              path="/chat/:conversationId"
              element={
                loggedIn ? <ChatLayout /> : <Navigate to="/login" replace />
              }
            />
            <Route
              path="/documents"
              element={
                loggedIn ? <DocumentsPage /> : <Navigate to="/login" replace />
              }
            />
            <Route
              path="/settings"
              element={
                loggedIn ? <SettingsPage /> : <Navigate to="/login" replace />
              }
            />
          </Routes>

          {/* Global toast notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#363636",
                color: "#fff",
              },
              success: {
                duration: 3000,
                style: {
                  background: "#10b981",
                },
              },
              error: {
                duration: 5000,
                style: {
                  background: "#ef4444",
                },
              },
            }}
          />
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
