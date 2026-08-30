import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Paperclip, X, FileText, FileCode, Maximize2 } from 'lucide-react';
import { AIMessage } from './AIMessage';

function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ChatArea({ messages, onSendMessage, loading, isTyping }) {
  const [input, setInput] = useState("");
  const [stagedFiles, setStagedFiles] = useState([]);
  const [previewModalImg, setPreviewModalImg] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, stagedFiles]);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result;
        // Extract base64 without prefix for API payload
        const base64Data = result.split(',')[1] || '';
        
        const newFile = {
          id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
          filename: file.name,
          content_type: file.type || 'application/octet-stream',
          size: file.size,
          data_base64: base64Data,
          previewUrl: result, // Full data URI for <img> tags
        };

        setStagedFiles(prev => [...prev, newFile]);
      };
      reader.readAsDataURL(file);
    });

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeStagedFile = (fileId) => {
    setStagedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((!input.trim() && stagedFiles.length === 0) || isTyping) return;
    
    // Send message and attachments
    onSendMessage(input, stagedFiles);
    setInput("");
    setStagedFiles([]);
  };

  return (
    <div className="flex-1 flex flex-col bg-transparent relative h-[calc(100vh-4rem)]">
      {/* Chat Messages List */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {loading ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="animate-pulse flex items-center gap-2">
              <Bot size={20} />
              <span>Syncing workspace...</span>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4 text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-xs">
              <Bot size={32} />
            </div>
            <div>
              <p className="font-semibold text-gray-800 text-lg">Start a conversation or upload project files</p>
              <p className="text-sm text-gray-500 mt-1 max-w-sm">
                Attach images, wireframes, or code. Project Partner will analyze them and remember them across future turns.
              </p>
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.message_id || msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'agent' && (
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 border border-blue-200 mt-1">
                  <Bot size={16} className="text-blue-600" />
                </div>
              )}
              
              <div className={`max-w-[85%] rounded-2xl px-5 py-3.5 shadow-xs ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-br-none' 
                  : 'bg-white text-gray-900 border border-black/5 rounded-bl-none overflow-hidden'
              }`}>
                {/* User or Agent Attachments Gallery */}
                {msg.attachments && msg.attachments.length > 0 && (
                  <div className="mb-3 space-y-2">
                    <div className="flex flex-wrap gap-2">
                      {msg.attachments.map(att => {
                        const isImage = att.content_type?.startsWith('image/') || att.previewUrl?.startsWith('data:image/');
                        const imgSrc = att.previewUrl || (att.data_base64 ? `data:${att.content_type};base64,${att.data_base64}` : null);

                        if (isImage && imgSrc) {
                          return (
                            <div 
                              key={att.id || att.filename} 
                              className="relative group rounded-lg overflow-hidden border border-black/10 bg-black/5 cursor-pointer max-w-[200px]"
                              onClick={() => setPreviewModalImg(imgSrc)}
                            >
                              <img 
                                src={imgSrc} 
                                alt={att.filename} 
                                className="h-28 w-auto object-cover rounded-lg group-hover:scale-105 transition-transform duration-200"
                              />
                              <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white">
                                <Maximize2 size={16} />
                              </div>
                              <span className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-[10px] px-1.5 py-0.5 truncate text-center">
                                {att.filename}
                              </span>
                            </div>
                          );
                        }

                        return (
                          <div 
                            key={att.id || att.filename}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium border ${
                              msg.role === 'user' 
                                ? 'bg-blue-700/80 border-blue-500 text-white' 
                                : 'bg-gray-50 border-gray-200 text-gray-800'
                            }`}
                          >
                            {att.filename.endsWith('.json') || att.filename.endsWith('.js') || att.filename.endsWith('.py') ? (
                              <FileCode size={14} className="text-amber-400 flex-shrink-0" />
                            ) : (
                              <FileText size={14} className="text-blue-400 flex-shrink-0" />
                            )}
                            <span className="truncate max-w-[150px]">{att.filename}</span>
                            {att.size && (
                              <span className="opacity-75 text-[10px]">({formatFileSize(att.size)})</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {msg.role === 'agent' ? (
                  <AIMessage content={msg.content} />
                ) : (
                  <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">{msg.content}</p>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 border border-black/5 mt-1">
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

      {/* Input Form & Staged Attachments */}
      <div className="p-4 bg-white/60 backdrop-blur-md border-t border-black/10">
        <div className="max-w-4xl mx-auto space-y-2">
          {/* Staged files strip */}
          {stagedFiles.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 p-2 bg-gray-50 rounded-xl border border-black/5">
              {stagedFiles.map(file => {
                const isImage = file.content_type.startsWith('image/');
                return (
                  <div 
                    key={file.id}
                    className="flex items-center gap-2 bg-white border border-gray-200 px-2.5 py-1.5 rounded-lg shadow-2xs text-xs"
                  >
                    {isImage ? (
                      <img src={file.previewUrl} alt={file.filename} className="w-6 h-6 object-cover rounded" />
                    ) : (
                      <FileText size={14} className="text-blue-500" />
                    )}
                    <div className="max-w-[120px] truncate">
                      <span className="font-medium text-gray-800 truncate block">{file.filename}</span>
                      <span className="text-[10px] text-gray-400">{formatFileSize(file.size)}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeStagedFile(file.id)}
                      className="p-1 text-gray-400 hover:text-red-500 transition-colors rounded-full hover:bg-gray-100 cursor-pointer"
                    >
                      <X size={13} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              multiple 
              accept="image/*,.pdf,.txt,.json,.md,.js,.jsx,.ts,.tsx,.py,.csv" 
              className="hidden" 
            />
            <button 
              type="button" 
              onClick={() => fileInputRef.current?.click()}
              className="absolute left-3 text-gray-400 hover:text-blue-600 transition-colors cursor-pointer p-1 rounded-full hover:bg-gray-100" 
              title="Attach images or files"
            >
              <Paperclip size={20} />
            </button>
            
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isTyping}
              placeholder={isTyping ? "AI is analyzing project context..." : "Ask a question, upload a mockup/schema, or give feedback..."}
              className="w-full bg-white border border-black/10 rounded-full pl-12 pr-12 py-4 text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-sm text-sm md:text-base"
            />
            
            <button 
              type="submit" 
              disabled={(!input.trim() && stagedFiles.length === 0) || isTyping}
              className="absolute right-2 p-2 bg-blue-600 rounded-full text-white hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors cursor-pointer"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>

      {/* Image Preview Modal */}
      {previewModalImg && (
        <div 
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setPreviewModalImg(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] flex flex-col items-center">
            <button 
              onClick={() => setPreviewModalImg(null)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300 p-2 cursor-pointer"
            >
              <X size={24} />
            </button>
            <img 
              src={previewModalImg} 
              alt="Preview full image" 
              className="max-w-full max-h-[85vh] rounded-lg shadow-2xl object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatArea;
