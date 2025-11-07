import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, Send, X } from "lucide-react";
import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface AgriBotProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AgriBot({ isOpen, onClose }: AgriBotProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm AgriBot, your agricultural assistant. I can help you understand your field data, stress indicators, and yield predictions. What would you like to know?"
    }
  ]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;

    const newMessage: Message = { role: "user", content: input };
    setMessages([...messages, newMessage]);
    setInput("");

    // TODO: Replace with actual RAG model integration
    // Placeholder response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "This is a placeholder response. Connect your RAG model here to provide intelligent agricultural insights based on your data."
      }]);
    }, 500);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-screen w-96 bg-background border-l shadow-lg z-50 flex flex-col" data-testid="panel-agribot">
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">AgriBot</h3>
        </div>
        <Button size="icon" variant="ghost" onClick={onClose} data-testid="button-close-agribot">
          <X className="w-4 h-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              data-testid={`message-${message.role}-${index}`}
            >
              <Card className={`p-3 max-w-[80%] ${
                message.role === "user" 
                  ? "bg-primary text-primary-foreground" 
                  : "bg-muted"
              }`}>
                <p className="text-sm">{message.content}</p>
              </Card>
            </div>
          ))}
        </div>
      </ScrollArea>

      <div className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about your fields..."
            data-testid="input-agribot-message"
          />
          <Button size="icon" onClick={handleSend} data-testid="button-send-message">
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {/* TODO: Connect to your RAG model for intelligent responses */}
          Powered by placeholder responses - integrate your RAG model
        </p>
      </div>
    </div>
  );
}
