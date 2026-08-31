import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { api } from '../api/client';
import { Sidebar } from '../components/workspace/Sidebar';
import { ChatArea } from '../components/workspace/ChatArea';


export default function Product() {
  const [userId] = useState("demo-user");
  const [projectId, setProjectId] = useState("recipe-organizer-01");
  const [projects, setProjects] = useState([]);
  const [projectData, setProjectData] = useState(null);
  const [projectFiles, setProjectFiles] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isTyping, setIsTyping] = useState(false);

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Fetch projects list
  useEffect(() => {
    api.listUserProjects(userId).then(res => setProjects(res.projects || [])).catch(console.error);
  }, [userId]);

  const handleNewProject = () => {
    const newId = "proj_" + Date.now().toString();
    setProjectId(newId);
    
    // Optimistically add it to the list
    const newProject = {
      project_id: newId,
      title: "New Project"
    };
    setProjects(prev => [newProject, ...prev]);
  };

  // Fetch project details, messages, and files
  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api.getProject(userId, projectId)
      .then(res => {
        setProjectData(res.project);
        setMessages(res.messages || []);
        setProjectFiles(res.files || []);
      })
      .catch(error => {
        console.warn("Failed to load project, assuming new:", error);
        setProjectData(null);
        setMessages([]);
        setProjectFiles([]);
      })
      .finally(() => setLoading(false));
  }, [userId, projectId]);



  const handleSendMessage = async (text, attachments = []) => {
    // Optimistic UI update
    const newMessage = { 
      message_id: Date.now().toString(), 
      role: "user", 
      content: text, 
      attachments: attachments,
      created_at: new Date().toISOString() 
    };
    const agentMsgId = Date.now().toString() + "-agent";
    
    // Add user message and an empty agent message placeholder
    setMessages(prev => [...prev, newMessage, { message_id: agentMsgId, role: "agent", content: "", created_at: new Date().toISOString() }]);
    setIsTyping(false); // Disable pulsing dots since text will stream immediately
    
    // Stream chunk handler
    const onChunk = (chunk) => {
      setMessages(prev => 
        prev.map(msg => 
          msg.message_id === agentMsgId 
            ? { ...msg, content: msg.content + chunk } 
            : msg
        )
      );
    };

    // Complete processing handler
    const onComplete = (metadata) => {
      if (metadata.plan) {
        setProjectData(prev => ({ ...prev, current_plan: metadata.plan }));
      }
      if (metadata.feedback_detected) {
        console.log("Feedback detected!", metadata.memory_updates);
      }
      if (attachments.length > 0) {
        // Refresh project files if we uploaded something
        api.getProjectFiles(userId, projectId).then(res => {
          if (res.files) setProjectFiles(res.files);
        }).catch(console.error);
      }
      
      // Refresh the projects list to get the updated project title from the backend
      api.listUserProjects(userId).then(res => setProjects(res.projects || [])).catch(console.error);
    };

    const onError = (error) => {
      console.error("Chat stream error:", error);
      setMessages(prev => 
        prev.map(msg => 
          msg.message_id === agentMsgId 
            ? { ...msg, content: msg.content + "\n\n*(Error: Connection to AI failed. Please try again.)*" } 
            : msg
        )
      );
    };

    await api.chatStream(userId, projectId, text, attachments, onChunk, onComplete, onError);
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await api.deleteFile(userId, projectId, fileId);
      setProjectFiles(prev => prev.filter(f => f.id !== fileId));
    } catch (error) {
      console.error("Failed to delete file:", error);
    }
  };

  return (
    <div className="flex h-screen pt-16 overflow-hidden relative">
      {/* Mobile Toggle Button */}
      <button 
        className="md:hidden absolute top-4 left-4 z-50 p-2 bg-white rounded-md shadow-md border border-gray-200"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
      >
        {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar Overlay for Mobile */}
      {isSidebarOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/20 z-40 top-16"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <div className={`
        absolute md:relative z-40 bg-[#f9f9f9] h-full transition-transform duration-300 flex-shrink-0
        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        <Sidebar 
          projects={projects} 
          activeProjectId={projectId} 
          onSelectProject={(id) => {
            setProjectId(id);
            setIsSidebarOpen(false);
          }}
          onNewProject={() => {
            handleNewProject();
            setIsSidebarOpen(false);
          }}
        />
      </div>
      
      <main className="flex-1 flex border-x border-black/5 relative shadow-sm min-w-0">
        <ChatArea 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          loading={loading} 
          isTyping={isTyping}
        />
      </main>
      



    </div>
  );
}
