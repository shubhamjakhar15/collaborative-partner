import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, FileCode, Mic, Paperclip, Database, Lightbulb, CheckCircle2, Layers, Zap } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen pt-24 pb-20 px-6 flex flex-col items-center text-center font-sans">
      
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="max-w-4xl mx-auto mt-10 w-full"
      >
        {/* Glassmorphic Glowing Orb */}
        <div className="relative w-48 h-48 mx-auto mb-10 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-purple-300 opacity-40 blur-[40px] mix-blend-multiply animate-pulse"></div>
          <div className="relative w-40 h-40 rounded-full bg-white/40 backdrop-blur-2xl shadow-[inset_0_-10px_20px_rgba(168,85,247,0.3),_inset_0_10px_20px_rgba(255,255,255,0.9),_0_20px_40px_-10px_rgba(168,85,247,0.3)] border border-white/60 flex items-center justify-center overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-100 via-purple-300 to-purple-500 opacity-70"></div>
            <div className="absolute top-3 left-5 w-14 h-14 bg-white rounded-full blur-[10px] opacity-90"></div>
          </div>
        </div>

        {/* Greeting Headline */}
        <h1 className="text-4xl md:text-[44px] font-medium tracking-tight text-gray-900 mb-10 leading-tight">
          <span className="bg-gradient-to-r from-purple-400 to-purple-500 bg-clip-text text-transparent block mb-1">
            Hello, Developer
          </span>
          How can I assist you today?
        </h1>

        {/* Command Bar Input */}
        <div 
          className="max-w-3xl mx-auto w-full bg-white border border-gray-200/60 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl p-3 mb-10 flex flex-col gap-3 transition-all hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] text-left cursor-text"
          onClick={() => navigate('/product')}
        >
          <div className="flex items-center px-2 pt-1">
             <input 
              type="text" 
              placeholder="Ask me anything..." 
              className="flex-1 bg-transparent border-none outline-none text-gray-700 placeholder-gray-400 text-[15px]"
              readOnly
             />
          </div>
          
          <div className="flex items-center justify-between mt-2">
            <div className="flex gap-2">
              <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                <FileCode size={18} />
              </button>
              <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
                <Mic size={18} />
              </button>
            </div>
            
            <div className="flex gap-2">
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-gray-200 text-gray-600 text-[13px] font-semibold hover:bg-gray-50 transition-colors">
                <Paperclip size={14} />
                Attach file
              </button>
            </div>
          </div>
        </div>

        {/* Suggestion Cards */}
        <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-5 text-left">
          <div onClick={() => navigate('/product')} className="p-6 rounded-2xl bg-white border border-gray-100/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(168,85,247,0.1)] transition-all duration-300 cursor-pointer group">
             <Database size={22} className="text-gray-400 mb-4 group-hover:text-purple-500 transition-colors"/>
             <h4 className="text-[14px] font-semibold text-gray-900 mb-2">Synthesize Data</h4>
             <p className="text-[13px] text-gray-500 leading-relaxed">Turn meeting notes into 5 key bullet points for the team.</p>
          </div>
          <div onClick={() => navigate('/product')} className="p-6 rounded-2xl bg-white border border-gray-100/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(168,85,247,0.1)] transition-all duration-300 cursor-pointer group">
             <Lightbulb size={22} className="text-gray-400 mb-4 group-hover:text-purple-500 transition-colors"/>
             <h4 className="text-[14px] font-semibold text-gray-900 mb-2">Creative Brainstorm</h4>
             <p className="text-[13px] text-gray-500 leading-relaxed">Generate 3 taglines for a new sustainable fashion brand.</p>
          </div>
          <div onClick={() => navigate('/product')} className="p-6 rounded-2xl bg-white border border-gray-100/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(168,85,247,0.1)] transition-all duration-300 cursor-pointer group">
             <CheckCircle2 size={22} className="text-gray-400 mb-4 group-hover:text-purple-500 transition-colors"/>
             <h4 className="text-[14px] font-semibold text-gray-900 mb-2">Check Facts</h4>
             <p className="text-[13px] text-gray-500 leading-relaxed">Compare key differences between GDPR and CCPA.</p>
          </div>
        </div>
      </motion.div>

      {/* Legacy Feature Cards (Restyled for minimalism with float effect) */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.2 }}
        className="mt-32 grid md:grid-cols-2 gap-6 max-w-5xl mx-auto text-left"
      >
        <div className="p-8 rounded-3xl bg-white border border-gray-100/50 shadow-[0_8px_30px_rgb(0,0,0,0.03)] hover:shadow-[0_8px_30px_rgba(168,85,247,0.08)] hover:-translate-y-1 transition-all duration-300">
          <Layers className="text-gray-400 mb-5" size={26} />
          <h3 className="text-[15px] font-semibold text-gray-900 mb-2.5">Structured Roadmaps</h3>
          <p className="text-[14px] text-gray-500 leading-relaxed">Watch the AI automatically break your goals down into actionable, sequential tasks.</p>
        </div>

        <div className="p-8 rounded-3xl bg-white border border-gray-100/50 shadow-[0_8px_30px_rgb(0,0,0,0.03)] hover:shadow-[0_8px_30px_rgba(168,85,247,0.08)] hover:-translate-y-1 transition-all duration-300">
          <Sparkles className="text-gray-400 mb-5" size={26} />
          <h3 className="text-[15px] font-semibold text-gray-900 mb-2.5">Adaptive Chat</h3>
          <p className="text-[14px] text-gray-500 leading-relaxed">A conversational interface that knows exactly what stage your project is in.</p>
        </div>
      </motion.div>
    </div>
  );
}
