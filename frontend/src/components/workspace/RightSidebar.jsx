import { useState } from 'react';
import { ListTodo, CheckCircle2, Circle, AlertCircle, FolderGit2, FileText, FileCode, Trash2, Image as ImageIcon } from 'lucide-react';
import { cn } from '../layout';

function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function RightSidebar({ projectData, projectFiles = [], onDeleteFile }) {
  const [activeTab, setActiveTab] = useState('roadmap'); // 'roadmap' | 'files'
  const plan = projectData?.current_plan;

  return (
    <div className="w-80 bg-white/60 backdrop-blur-md border-l border-black/5 flex flex-col h-[calc(100vh-4rem)]">
      {/* Tab Navigation */}
      <div className="p-2 border-b border-black/5 bg-gray-50/50 flex gap-1">
        <button
          onClick={() => setActiveTab('roadmap')}
          className={cn(
            "flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer",
            activeTab === 'roadmap'
              ? "bg-white text-gray-900 shadow-xs border border-black/5"
              : "text-gray-500 hover:text-gray-900 hover:bg-gray-100/50"
          )}
        >
          <ListTodo size={15} />
          <span>Roadmap</span>
        </button>

        <button
          onClick={() => setActiveTab('files')}
          className={cn(
            "flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer",
            activeTab === 'files'
              ? "bg-white text-gray-900 shadow-xs border border-black/5"
              : "text-gray-500 hover:text-gray-900 hover:bg-gray-100/50"
          )}
        >
          <FolderGit2 size={15} />
          <span>Files</span>
          {projectFiles?.length > 0 && (
            <span className="ml-1 bg-gray-900 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold">
              {projectFiles.length}
            </span>
          )}
        </button>
      </div>
      
      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'roadmap' ? (
          !plan ? (
            <div className="text-center text-gray-500 text-sm mt-10">
              <ListTodo size={32} className="mx-auto mb-3 opacity-30 text-purple-500" />
              <p className="font-medium text-gray-700">No active plan yet.</p>
              <p className="text-xs mt-1 text-gray-500">Discuss your goals in chat to generate a roadmap.</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <h3 className="font-bold text-gray-900 mb-1 text-base">{plan.title}</h3>
                <p className="text-xs text-gray-600 font-medium leading-relaxed">{plan.summary}</p>
              </div>
              
              <div className="space-y-3">
                {plan.steps.map((step, idx) => (
                  <div 
                    key={step.id} 
                    className="flex gap-3 p-3 rounded-xl bg-white border border-black/5 hover:border-purple-200 transition-colors shadow-2xs"
                  >
                    <div className="mt-0.5">
                      {step.status === 'completed' ? (
                        <CheckCircle2 size={16} className="text-green-500" />
                      ) : step.status === 'in_progress' ? (
                        <Circle size={16} className="text-purple-500 fill-blue-100" />
                      ) : step.status === 'blocked' ? (
                        <AlertCircle size={16} className="text-red-500" />
                      ) : (
                        <Circle size={16} className="text-gray-300" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className={cn(
                        "text-sm leading-snug font-medium",
                        step.status === 'completed' ? "text-gray-400 line-through" : "text-gray-800"
                      )}>
                        {step.description}
                      </p>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-wider font-bold text-gray-500">
                          {step.assignee}
                        </span>
                        <span className="text-[10px] font-semibold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                          Step {idx + 1}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        ) : (
          /* Project Files & Multimodal Memory Tab */
          <div>
            <div className="mb-4">
              <h3 className="text-xs uppercase font-bold text-gray-500 tracking-wider">Project Memory Assets</h3>
              <p className="text-[11px] text-gray-500 mt-0.5">
                AI references these files in every conversation turn.
              </p>
            </div>

            {!projectFiles || projectFiles.length === 0 ? (
              <div className="text-center text-gray-500 text-sm mt-10">
                <FolderGit2 size={32} className="mx-auto mb-3 opacity-30 text-purple-500" />
                <p className="font-medium text-gray-700">No project files yet.</p>
                <p className="text-xs mt-1 text-gray-500 max-w-[200px] mx-auto">
                  Click the paperclip in chat to attach UI images, diagrams, or code.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {projectFiles.map(file => {
                  const isImage = file.content_type?.startsWith('image/') || file.filename?.match(/\.(png|jpg|jpeg|webp|gif)$/i);
                  const imgSrc = file.url || (file.data_base64 ? `data:${file.content_type};base64,${file.data_base64}` : null);

                  return (
                    <div 
                      key={file.id} 
                      className="p-2.5 rounded-xl bg-white border border-black/5 hover:border-purple-200 transition-all shadow-2xs flex items-center gap-3 group"
                    >
                      <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 overflow-hidden border border-black/5">
                        {isImage && imgSrc ? (
                          <img src={imgSrc} alt={file.filename} className="w-full h-full object-cover" />
                        ) : isImage ? (
                          <ImageIcon size={16} className="text-purple-500" />
                        ) : file.filename?.match(/\.(json|js|jsx|ts|tsx|py)$/i) ? (
                          <FileCode size={16} className="text-amber-500" />
                        ) : (
                          <FileText size={16} className="text-purple-500" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-gray-800 truncate" title={file.filename}>
                          {file.filename}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5 text-[10px] text-gray-400">
                          {file.size && <span>{formatFileSize(file.size)}</span>}
                          {file.content_type && (
                            <span className="bg-gray-100 text-gray-600 px-1.5 py-0.2 rounded font-mono truncate max-w-[90px]">
                              {file.content_type.split('/')[1] || file.content_type}
                            </span>
                          )}
                        </div>
                      </div>

                      {onDeleteFile && (
                        <button
                          onClick={() => onDeleteFile(file.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
                          title="Delete from project memory"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default RightSidebar;
