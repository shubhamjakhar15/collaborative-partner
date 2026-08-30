import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Paperclip } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export function ChatArea({ messages, onSendMessage, loading, isTyping }) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;
    onSendMessage(input);
    setInput("");
  };

  return (
    <div className="flex-1 flex flex-col bg-transparent relative h-[calc(100vh-4rem)]">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {loading ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="animate-pulse flex items-center gap-2">
              <Bot size={20} />
              <span>Syncing workspace...</span>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
            <Bot size={48} className="text-blue-500/50" />
            <p>Start a new conversation to build your roadmap.</p>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.message_id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'agent' && (
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 border border-blue-200">
                  <Bot size={16} className="text-blue-600" />
                </div>
              )}
              
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 shadow-sm ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-br-none' 
                  : 'bg-white text-gray-900 border border-black/5 rounded-bl-none'
              }`}>
                {msg.role === 'agent' ? (
                  <div className="prose prose-sm md:prose-base prose-blue max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">{msg.content}</p>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 border border-black/5">
                  <User size={16} className="text-gray-600" />
                </div>
              )}
            </div>
          ))
        )}

        {isTyping && (
          <div className="flex gap-4 justify-start">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 border border-blue-200">
              <Bot size={16} className="text-blue-600" />
            </div>
            <div className="max-w-[80%] rounded-2xl px-5 py-4 shadow-sm bg-white border border-black/5 rounded-bl-none flex items-center gap-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white/50 backdrop-blur-md border-t border-black/10">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
          <button type="button" className="absolute left-3 text-gray-400 hover:text-blue-600 transition-colors" title="Attach files">
            <Paperclip size={20} />
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
            placeholder={isTyping ? "AI is thinking..." : "Describe your goal, provide feedback, or attach context..."}
            className="w-full bg-white border border-black/10 rounded-full pl-12 pr-12 py-4 text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-sm"
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isTyping}
            className="absolute right-2 p-2 bg-blue-600 rounded-full text-white hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
