import { FolderKanban, Plus, Settings2 } from 'lucide-react';
import { cn } from '../layout';

export function Sidebar({ projects, activeProjectId, onSelectProject, onOpenMemoryVault }) {
  return (
    <div className="w-64 flex flex-col bg-white/50 backdrop-blur-md border-r border-black/5">
      <div className="p-4 border-b border-black/5 flex justify-between items-center">
        <h2 className="text-sm font-semibold text-gray-900">Projects</h2>
        <button className="p-1 hover:bg-black/5 rounded-md transition-colors text-gray-600 hover:text-gray-900">
          <Plus size={16} />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {projects.length === 0 ? (
          <p className="text-xs text-gray-500 text-center mt-4 font-medium">No projects found</p>
        ) : (
          projects.map(proj => (
            <button
              key={proj.project_id}
              onClick={() => onSelectProject(proj.project_id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all text-left font-medium my-1",
                activeProjectId === proj.project_id 
                  ? "bg-blue-600 text-white shadow-md" 
                  : "text-gray-600 hover:bg-white hover:text-gray-900 hover:shadow-sm"
              )}
            >
              <FolderKanban size={16} />
              <span className="truncate">{proj.title || proj.project_id}</span>
            </button>
          ))
        )}
      </div>

      <div className="p-4 border-t border-black/5">
        <button 
          onClick={onOpenMemoryVault}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-white hover:text-gray-900 hover:shadow-sm transition-all"
        >
          <Settings2 size={16} />
          Memory Vault
        </button>
      </div>
    </div>
  );
}
