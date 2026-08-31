import { Plus, Settings2, MessageSquare, Search, PanelLeftClose } from 'lucide-react';
import { cn } from '../layout';

export function Sidebar({ projects, activeProjectId, activeMessages = [], onSelectProject, onNewProject }) {
  const userQuestions = activeMessages.filter(msg => msg.role === 'user');

  const scrollToMessage = (msgId) => {
    const el = document.getElementById(msgId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="w-[260px] flex flex-col bg-[#f9f9f9] border-r border-black/5 h-[calc(100vh-4rem)]">
      {/* Header & New Chat */}
      <div className="p-4 flex flex-col gap-4">
        <button 
          onClick={onNewProject}
          className="w-full flex items-center justify-center gap-2 bg-[#1a1a1a] text-white px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-black transition-all"
        >
          <Plus size={16} />
          New chat
        </button>

        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search" 
            className="w-full bg-white border border-gray-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-gray-700 outline-none focus:border-gray-300 shadow-sm"
          />
        </div>
      </div>
      
      {/* Project History */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <h3 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider px-2 mb-2 mt-2">History</h3>
        
        {projects.length === 0 ? (
          <p className="text-xs text-gray-500 text-center mt-4">No history yet</p>
        ) : (
          projects.map(proj => (
            <div key={proj.project_id} className="mb-1">
              <button
                onClick={() => onSelectProject(proj.project_id)}
                className={cn(
                  "w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-[13px] transition-all text-left truncate",
                  activeProjectId === proj.project_id 
                    ? "bg-gray-200/60 text-gray-900 font-medium" 
                    : "text-gray-600 hover:bg-gray-100 font-normal"
                )}
                title={proj.title || proj.project_id}
              >
                <span className="truncate">{proj.title || "New Conversation"}</span>
              </button>
              
              {activeProjectId === proj.project_id && userQuestions.length > 0 && (
                <div className="pl-4 pr-1 py-1 space-y-0.5 border-l-2 border-black/5 ml-3 my-1">
                  {userQuestions.map((msg, idx) => (
                    <button
                      key={msg.message_id || idx}
                      onClick={() => scrollToMessage(msg.message_id)}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[12px] transition-all text-left text-gray-500 hover:text-gray-900 hover:bg-gray-200/50"
                      title={msg.content}
                    >
                      <span className="truncate">{msg.content}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>


    </div>
  );
}
