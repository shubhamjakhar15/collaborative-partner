import { motion, AnimatePresence } from 'framer-motion';
import { X, Brain, ShieldCheck } from 'lucide-react';

export function MemoryVault({ isOpen, onClose, preferences }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-[400px] bg-[#0d0a15] border-l border-white/10 z-50 flex flex-col shadow-2xl"
          >
            <div className="p-6 border-b border-white/10 flex justify-between items-center bg-black/40">
              <div className="flex items-center gap-3">
                <div className="bg-purple-600/20 p-2 rounded-lg border border-purple-500/30">
                  <Brain size={20} className="text-purple-400" />
                </div>
                <div>
                  <h2 className="font-semibold text-white">Memory Vault</h2>
                  <p className="text-xs text-gray-400">Cross-project learned preferences</p>
                </div>
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {preferences.length === 0 ? (
                <div className="text-center text-gray-500 mt-10">
                  <p>No preferences learned yet.</p>
                  <p className="text-sm mt-2">The AI learns your habits automatically as you chat and provide feedback.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {preferences.map((pref, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-white/5 border border-white/10">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium px-2 py-1 bg-purple-500/20 text-purple-300 rounded-md">
                          {pref.category || 'General'}
                        </span>
                        {pref.confidence > 0.8 && (
                          <div className="flex items-center gap-1 text-[10px] text-green-400">
                            <ShieldCheck size={12} />
                            High Confidence
                          </div>
                        )}
                      </div>
                      <p className="text-sm text-white mb-2">
                        <span className="text-gray-400 mr-2">{pref.key}:</span>
                        {pref.value}
                      </p>
                      {pref.evidence && (
                        <div className="mt-3 p-2 rounded bg-black/30 text-xs text-gray-400 border-l-2 border-purple-500/50">
                          "{pref.evidence}"
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
