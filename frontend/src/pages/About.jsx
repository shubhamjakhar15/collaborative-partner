import { motion } from 'framer-motion';

export default function About() {
  return (
    <div className="min-h-screen pt-32 pb-12 px-6 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        <h1 className="text-4xl md:text-6xl font-bold mb-8">About Project Partner</h1>
        <div className="prose prose-invert prose-lg">
          <p className="text-xl text-gray-300 leading-relaxed mb-6">
            We believe that AI shouldn't just be a conversational tool—it should be a true partner in your workflow.
            Project Partner was built to bridge the gap between ideation and execution.
          </p>
          <p className="text-lg text-gray-400 leading-relaxed mb-6">
            Traditional AI chatbots forget your context the moment you start a new conversation. Our system leverages an advanced Memory Vault, learning your specific preferences, constraints, and habits across all your projects. 
          </p>
          <p className="text-lg text-gray-400 leading-relaxed">
            By automatically structuring conversations into actionable roadmaps, Project Partner ensures that every chat moves your project forward. Welcome to the future of collaborative intelligence.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
