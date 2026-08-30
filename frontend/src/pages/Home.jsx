import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Sparkles, ArrowRight, Layers, Zap } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen pt-24 pb-12 px-6 flex flex-col items-center text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="max-w-4xl mx-auto mt-20"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/60 border border-black/5 text-sm text-gray-600 mb-8 shadow-sm">
          <Sparkles size={16} className="text-blue-500" />
          <span>The next generation of AI collaboration</span>
        </div>
        <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-gray-900 mb-8">
          Build faster with your <br className="hidden md:block" />
          <span className="text-gray-900">
            Intelligent Partner
          </span>
        </h1>
        <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto font-medium">
          Project Partner isn't just a chat bot. It's an intelligent workspace that understands your goals, tracks your roadmaps, and adapts to your preferences over time.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            to="/product"
            className="flex items-center gap-2 bg-blue-600 text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-blue-700 hover:scale-105 transition-all shadow-lg shadow-blue-500/30"
          >
            Start Building
            <ArrowRight size={20} />
          </Link>
          <Link
            to="/about"
            className="flex items-center gap-2 bg-white text-gray-900 border border-black/10 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-50 transition-colors shadow-sm"
          >
            Learn More
          </Link>
        </div>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.2 }}
        className="mt-32 grid md:grid-cols-3 gap-8 max-w-6xl mx-auto text-left"
      >
        <div className="p-8 rounded-3xl bg-white/60 border border-black/5 shadow-sm backdrop-blur-md">
          <Layers className="text-blue-500 mb-4" size={32} />
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Structured Roadmaps</h3>
          <p className="text-gray-600 font-medium">Watch the AI automatically break your goals down into actionable, sequential tasks.</p>
        </div>
        <div className="p-8 rounded-3xl bg-white/60 border border-black/5 shadow-sm backdrop-blur-md">
          <Zap className="text-pink-500 mb-4" size={32} />
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Memory Vault</h3>
          <p className="text-gray-600 font-medium">The AI learns your preferences across all projects. Teach it once, and it remembers forever.</p>
        </div>
        <div className="p-8 rounded-3xl bg-white/60 border border-black/5 shadow-sm backdrop-blur-md">
          <Sparkles className="text-indigo-500 mb-4" size={32} />
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Adaptive Chat</h3>
          <p className="text-gray-600 font-medium">A conversational interface that knows exactly what stage your project is in.</p>
        </div>
      </motion.div>
    </div>
  );
}
