import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Sidebar } from '../components/workspace/Sidebar';
import { ChatArea } from '../components/workspace/ChatArea';
import { RightSidebar } from '../components/workspace/RightSidebar';
import { MemoryVault } from '../components/workspace/MemoryVault';

export default function Product() {
  const [userId] = useState("demo-user");
  const [projectId, setProjectId] = useState("recipe-organizer-01");
  const [projects, setProjects] = useState([]);
  const [projectData, setProjectData] = useState(null);
  const [projectFiles, setProjectFiles] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [isMemoryVaultOpen, setIsMemoryVaultOpen] = useState(false);
  const [preferences, setPreferences] = useState([]);

  // Fetch projects list
  useEffect(() => {
    api.listUserProjects(userId).then(res => setProjects(res.projects || [])).catch(console.error);
  }, [userId]);

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
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [userId, projectId]);

  // Fetch preferences
  useEffect(() => {
    if (isMemoryVaultOpen) {
      api.getUserPreferences(userId).then(res => setPreferences(res.preferences || [])).catch(console.error);
    }
  }, [isMemoryVaultOpen, userId]);

  const handleSendMessage = async (text, attachments = []) => {
    // Optimistic UI update
    const newMessage = { 
      message_id: Date.now().toString(), 
      role: "user", 
      content: text, 
      attachments: attachments,
      created_at: new Date().toISOString() 
    };
    setMessages(prev => [...prev, newMessage]);
    setIsTyping(true);
    
    try {
      const response = await api.chat(userId, projectId, text, {}, attachments);
      
      const agentMessage = { 
        message_id: Date.now().toString() + "-agent", 
        role: "agent", 
        content: response.message,
        attachments: response.attachments || [],
        created_at: response.timestamp
      };
      
      setMessages(prev => [...prev, agentMessage]);
      
      if (response.plan) {
        setProjectData(prev => ({ ...prev, current_plan: response.plan }));
      }

      if (response.project_files && response.project_files.length > 0) {
        setProjectFiles(response.project_files);
      } else if (attachments.length > 0) {
        // Refresh project files
        api.getProjectFiles(userId, projectId).then(res => {
          if (res.files) setProjectFiles(res.files);
        }).catch(console.error);
      }
      
      if (response.feedback_detected) {
        console.log("Feedback detected!", response.memory_updates);
      }
    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsTyping(false);
    }
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
    <div className="flex h-screen pt-16 overflow-hidden">
      <Sidebar 
        projects={projects} 
        activeProjectId={projectId} 
        onSelectProject={setProjectId}
        onOpenMemoryVault={() => setIsMemoryVaultOpen(true)}
      />
      
      <main className="flex-1 flex border-x border-black/5 relative shadow-sm">
        <ChatArea 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          loading={loading} 
          isTyping={isTyping}
        />
      </main>
      
      <RightSidebar 
        projectData={projectData} 
        projectFiles={projectFiles}
        onDeleteFile={handleDeleteFile}
      />

      <MemoryVault 
        isOpen={isMemoryVaultOpen} 
        onClose={() => setIsMemoryVaultOpen(false)}
        preferences={preferences}
      />
    </div>
  );
}
