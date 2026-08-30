import { ListTodo, CheckCircle2, Circle, AlertCircle } from 'lucide-react';
import { cn } from '../layout';

export function RightSidebar({ projectData }) {
  const plan = projectData?.current_plan;

  return (
    <div className="w-80 bg-white/50 backdrop-blur-md border-l border-black/5 flex flex-col h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-black/5 flex items-center gap-2">
        <ListTodo size={18} className="text-blue-500" />
        <h2 className="font-semibold text-gray-900">Active Roadmap</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        {!plan ? (
          <div className="text-center text-gray-500 text-sm mt-10">
            <ListTodo size={32} className="mx-auto mb-3 opacity-30 text-blue-500" />
            <p className="font-medium text-gray-700">No active plan yet.</p>
            <p className="text-xs mt-1 text-gray-500">Discuss your goals in chat to generate a roadmap.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h3 className="font-bold text-gray-900 mb-1">{plan.title}</h3>
              <p className="text-xs text-gray-600 font-medium">{plan.summary}</p>
            </div>
            
            <div className="space-y-3">
              {plan.steps.map((step, idx) => (
                <div 
                  key={step.id} 
                  className="flex gap-3 p-3 rounded-xl bg-white border border-black/5 hover:border-blue-200 transition-colors shadow-sm"
                >
                  <div className="mt-0.5">
                    {step.status === 'completed' ? (
                      <CheckCircle2 size={16} className="text-green-500" />
                    ) : step.status === 'in_progress' ? (
                      <Circle size={16} className="text-blue-500 fill-blue-100" />
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
        )}
      </div>
    </div>
  );
}
