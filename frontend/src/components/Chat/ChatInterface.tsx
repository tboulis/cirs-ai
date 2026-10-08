import React, { useState, useEffect, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { chatApi } from "../../services/api";
import { Conversation, Message, ChatRequest } from "../../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { EmptyConversationMessage } from "./EmptyConversationMessage";
import { Loader } from "./Loader";
import { ChatInput } from "./ChatInput";

interface ChatInterfaceProps {
  conversation?: Conversation;
  selectedModel: string;
  onConversationUpdate: (conversation: Conversation) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  conversation,
  selectedModel,
  onConversationUpdate,
}) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch conversation messages when conversation changes
  const { data: fetchedMessages = [], isLoading: messagesLoading } = useQuery({
    queryKey: ["messages", conversation?.id],
    queryFn: () =>
      conversation ? chatApi.getConversationMessages(conversation.id) : [],
  });

  // Sync fetched messages into local state (handles cached data on tab switch)
  useEffect(() => {
    if (conversation) {
      setMessages(fetchedMessages);
    } else {
      setMessages([]);
    }
  }, [fetchedMessages, conversation]);

  // Send message mutation
  const sendMessageMutation = useMutation(
    (request: ChatRequest) => chatApi.sendMessage(request),
    {
      onMutate: () => {
        setIsTyping(true);
      },
      onSuccess: (response) => {
        // Add assistant message
        const assistantMessage: Message = {
          id: Date.now(), // Temporary ID
          content: response.message,
          role: "assistant",
          model_used: response.model_used,
          tokens_used: response.tokens_used,
          response_time: response.response_time,
          created_at: new Date().toISOString(),
          sources: response.sources,
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Update conversation if new one was created
        if (
          response.conversation_id &&
          (!conversation || conversation.id !== response.conversation_id)
        ) {
          onConversationUpdate({
            id: response.conversation_id,
            title: input.substring(0, 50),
            created_at: new Date().toISOString(),
            is_active: true,
            message_count: 2, // User + assistant message
          });
        }

        setIsTyping(false);
      },
      onError: (error) => {
        setIsTyping(false);
        toast.error(`Failed to send message: ${error}`);
      },
    }
  );

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendMessage = async () => {
    if (!input.trim() || sendMessageMutation.isLoading) return;

    const userMessage: Message = {
      id: Date.now(),
      content: input.trim(),
      role: "user",
      created_at: new Date().toISOString(),
    };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);

    const request: ChatRequest = {
      message: input.trim(),
      conversation_id: conversation?.id,
      model: selectedModel,
      use_context: true,
    };

    setInput("");
    await sendMessageMutation.mutateAsync(request);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!conversation && messages.length === 0 && <EmptyConversationMessage />}

        {messagesLoading && <Loader />}

        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            isLast={index === messages.length - 1}
          />
        ))}

        {isTyping && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <ChatInput
        input={input}
        setInput={setInput}
        handleSendMessage={handleSendMessage}
        selectedModel={selectedModel}
        inputRef={inputRef}
        handleKeyPress={handleKeyPress}
        sendMessageMutation={sendMessageMutation}
      />
    </div>
  );
};

export default ChatInterface;
