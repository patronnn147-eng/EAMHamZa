import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, X, Minimize2, Maximize2, Send, Loader2, Copy, RefreshCw, ChevronRight } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface ChatMessage {
  id: string;
  query: string;
  intent: string;
  results: any[];
  formatted_message: string;
  timestamp: string;
}

interface ChatResponse {
  intent: string;
  results: any[];
  confidence: number;
  formatted_message: string;
  suggestions: string[];
  query: string;
}

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    if (isOpen && suggestions.length === 0) {
      fetchSuggestions();
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API}/api/v1/chat/suggestions`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestions(data);
      }
    } catch (err) {
      console.error('Failed to fetch suggestions', err);
    }
  };

  const handleSubmit = async (query?: string) => {
    const finalQuery = query || input;
    if (!finalQuery.trim() || loading) return;

    setLoading(true);
    setInput('');

    try {
      const res = await fetch(`${API}/api/v1/chat/query`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: finalQuery }),
      });

      if (res.ok) {
        const data: ChatResponse = await res.json();
        const message: ChatMessage = {
          id: Date.now().toString(),
          query: finalQuery,
          intent: data.intent,
          results: data.results,
          formatted_message: data.formatted_message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, message]);
        if (data.suggestions) {
          setSuggestions(data.suggestions);
        }
      } else {
        toast({
          title: 'Error',
          description: 'Failed to process query',
          variant: 'destructive',
        });
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to process query',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(JSON.stringify(text, null, 2));
    toast({
      title: 'Copied',
      description: 'Results copied to clipboard',
      variant: 'default',
    });
  };

  if (!isOpen) {
    return (
      <Button
        className="fixed bottom-4 right-4 h-12 w-12 rounded-full shadow-lg z-50"
        onClick={() => setIsOpen(true)}
      >
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <Card className="fixed bottom-4 right-4 w-80 md:w-96 shadow-xl z-50 border-2">
      <CardHeader className="pb-2 border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            AI Assistant
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsMinimized(!isMinimized)}
            >
              {isMinimized ? (
                <Maximize2 className="h-4 w-4" />
              ) : (
                <Minimize2 className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      {!isMinimized && (
        <CardContent className="p-0">
          <ScrollArea className="h-80">
            <div className="p-4 space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Ask me about your assets!</p>
                  <p className="text-xs mt-1">
                    Try "Show machines in Zone A" or "Show alerts"
                  </p>
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} className="space-y-2">
                  <div className="flex justify-end">
                    <div className="bg-primary text-primary-foreground px-3 py-2 rounded-lg text-sm max-w-[80%]">
                      {msg.query}
                    </div>
                  </div>
                  <div className="bg-muted px-3 py-2 rounded-lg">
                    <p className="text-sm font-medium mb-1">{msg.formatted_message}</p>
                    <Badge variant="outline" className="text-xs mb-2">
                      {msg.intent}
                    </Badge>
                    {msg.results.length > 0 && (
                      <div className="mt-2">
                        <div className="flex justify-end">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleCopy(msg.results)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                        <div className="text-xs space-y-1 max-h-32 overflow-y-auto">
                          {msg.results.slice(0, 5).map((r: any, i: number) => (
                            <div key={i} className="flex items-center gap-2 text-muted-foreground">
                              <ChevronRight className="h-3 w-3" />
                              <span>
                                {r.name || r.title || r.id || JSON.stringify(r).slice(0, 50)}
                              </span>
                            </div>
                          ))}
                          {msg.results.length > 5 && (
                            <p className="text-muted-foreground">
                              +{msg.results.length - 5} more...
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Thinking...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {suggestions.length > 0 && messages.length === 0 && (
            <div className="px-4 pb-2">
              <p className="text-xs text-muted-foreground mb-2">Try:</p>
              <div className="flex flex-wrap gap-1">
                {suggestions.slice(0, 4).map((s, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="text-xs h-6"
                    onClick={() => handleSubmit(s)}
                  >
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="p-4 border-t">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSubmit();
              }}
              className="flex gap-2"
            >
              <Input
                placeholder="Ask about machines, alerts, work orders..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <Button type="submit" size="icon" disabled={loading || !input.trim()}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchSuggestions();
    fetchHistory();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API}/api/v1/chat/suggestions`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestions(data);
      }
    } catch (err) {
      console.error('Failed to fetch suggestions', err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API}/api/v1/chat/history?limit=10`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        // Convert history to messages
        const historyMessages: ChatMessage[] = data.history.map((h: any, i: number) => ({
          id: `history-${i}`,
          query: h.query,
          intent: h.intent,
          results: [],
          formatted_message: `${h.results_count} result(s)`,
          timestamp: h.timestamp,
        }));
        setMessages(historyMessages);
      }
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
  };

  const handleSubmit = async (query?: string) => {
    const finalQuery = query || input;
    if (!finalQuery.trim() || loading) return;

    setLoading(true);
    setInput('');

    try {
      const res = await fetch(`${API}/api/v1/chat/query`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: finalQuery }),
      });

      if (res.ok) {
        const data: ChatResponse = await res.json();
        const message: ChatMessage = {
          id: Date.now().toString(),
          query: finalQuery,
          intent: data.intent,
          results: data.results,
          formatted_message: data.formatted_message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, message]);
        if (data.suggestions) {
          setSuggestions(data.suggestions);
        }
      } else {
        toast({
          title: 'Error',
          description: 'Failed to process query',
          variant: 'destructive',
        });
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to process query',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: any) => {
    navigator.clipboard.writeText(JSON.stringify(text, null, 2));
    toast({
      title: 'Copied',
      description: 'Results copied to clipboard',
      variant: 'default',
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MessageSquare className="h-6 w-6" />
          AI Assistant
        </h1>
        <p className="text-muted-foreground">
          Ask natural language questions about your assets, alerts, and work orders
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        <Card className="lg:col-span-3">
          <CardContent className="p-0">
            <ScrollArea className="h-[500px]">
              <div className="p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center text-muted-foreground py-12">
                    <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
                    <p className="text-sm mb-4">
                      Ask me about your machines, alerts, work orders, and more
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {suggestions.slice(0, 6).map((s, i) => (
                        <Button
                          key={i}
                          variant="outline"
                          size="sm"
                          onClick={() => handleSubmit(s)}
                        >
                          {s}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg) => (
                  <div key={msg.id} className="space-y-2">
                    <div className="flex justify-end">
                      <div className="bg-primary text-primary-foreground px-4 py-2 rounded-lg max-w-[80%]">
                        {msg.query}
                      </div>
                    </div>
                    <div className="bg-muted px-4 py-3 rounded-lg ml-4">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline">{msg.intent}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="font-medium mb-2">{msg.formatted_message}</p>
                      {msg.results.length > 0 && (
                        <div className="mt-3">
                          <div className="flex justify-end mb-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCopy(msg.results)}
                            >
                              <Copy className="mr-1 h-3 w-3" />
                              Copy
                            </Button>
                          </div>
                          <div className="bg-background rounded border overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead className="border-b">
                                <tr className="text-left">
                                  {Object.keys(msg.results[0] || {}).map((key) => (
                                    <th key={key} className="px-3 py-2 font-medium">
                                      {key.replace('_', ' ')}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {msg.results.slice(0, 10).map((r, i) => (
                                  <tr key={i} className="border-b last:border-0">
                                    {Object.values(r).map((v: any, j) => (
                                      <td key={j} className="px-3 py-2">
                                        {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {msg.results.length > 10 && (
                              <div className="px-3 py-2 text-xs text-muted-foreground text-center">
                                Showing 10 of {msg.results.length} results
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            <div className="p-4 border-t">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSubmit();
                }}
                className="flex gap-2"
              >
                <Input
                  placeholder="Ask a question..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  className="text-base"
                />
                <Button type="submit" size="lg" disabled={loading || !input.trim()}>
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </form>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Suggestions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {suggestions.map((s, i) => (
                <Button
                  key={i}
                  variant="ghost"
                  className="w-full justify-start text-left h-auto py-2"
                  onClick={() => handleSubmit(s)}
                >
                  {s}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ChatWidget;
