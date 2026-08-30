import { motion } from 'framer-motion';
import { Bot, LineChart, BrainCircuit, MessageSquareCode } from 'lucide-react';

export default function Service() {
  const services = [
    {
      title: "Contextual AI Chat",
      description: "Chat with an AI that understands the specific stage of your project—from discovery to execution.",
      icon: <MessageSquareCode size={40} className="text-purple-400" />
    },
    {
      title: "Automated Roadmapping",
      description: "Instantly convert high-level goals into a structured, step-by-step implementation plan.",
      icon: <LineChart size={40} className="text-pink-400" />
    },
    {
      title: "Cross-Project Memory",
      description: "The AI learns your habits and technical preferences, applying them seamlessly to future projects.",
      icon: <BrainCircuit size={40} className="text-blue-400" />
    },
    {
      title: "Adaptive Workflows",
      description: "Give feedback on how you work, and the AI will dynamically adjust its communication style.",
      icon: <Bot size={40} className="text-green-400" />
    }
  ];

  return (
    <div className="min-h-screen pt-32 pb-12 px-6 max-w-6xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        <h1 className="text-4xl md:text-6xl font-bold mb-4 text-center">Our Services</h1>
        <p className="text-xl text-gray-400 text-center mb-16 max-w-2xl mx-auto">
          Everything you need to turn vague ideas into shipped products.
        </p>

        <div className="grid md:grid-cols-2 gap-8">
          {services.map((service, i) => (
            <div key={i} className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
              <div className="mb-6">{service.icon}</div>
              <h3 className="text-2xl font-semibold mb-3">{service.title}</h3>
              <p className="text-gray-400 text-lg leading-relaxed">{service.description}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
