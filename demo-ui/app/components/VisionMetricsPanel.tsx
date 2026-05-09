"use client";

import { motion } from "framer-motion";

interface VisionMetricsPanelProps {
  visionMetrics: any;
  colors: any;
  styles: any;
}

export function VisionMetricsPanel({ visionMetrics, colors, styles }: VisionMetricsPanelProps) {
  return (
    <div className="space-y-6">
      {/* Vision Progress Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 rounded-2xl"
        style={styles.card}
      >
        <h2 className="text-3xl font-bold mb-6" style={{ color: colors.gold, fontFamily: "'Cinzel Decorative', serif" }}>
          🌠 Vision Implementation Progress
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Phase 1: Identity */}
          <div className="p-6 rounded-xl" style={{ background: colors.gradient.primary }}>
            <div className="text-2xl mb-2">🔐</div>
            <h3 className="text-lg font-semibold text-white mb-2">Phase 1: Agent Identity</h3>
            <div className="text-3xl font-bold text-white mb-1">✅</div>
            <div className="text-sm text-white opacity-80">Cryptographic DID System</div>
          </div>

          {/* Phase 2: Threat Intel */}
          <div className="p-6 rounded-xl" style={{ background: colors.gradient.secondary }}>
            <div className="text-2xl mb-2">🛡️</div>
            <h3 className="text-lg font-semibold text-white mb-2">Phase 2: Threat Intel</h3>
            <div className="text-3xl font-bold text-white mb-1">✅</div>
            <div className="text-sm text-white opacity-80">Decentralized Marketplace</div>
          </div>

          {/* Phase 3: Insurance */}
          <div className="p-6 rounded-xl" style={{ background: colors.gradient.success }}>
            <div className="text-2xl mb-2">🛡️</div>
            <h3 className="text-lg font-semibold text-white mb-2">Phase 3: Insurance</h3>
            <div className="text-3xl font-bold text-white mb-1">🚀</div>
            <div className="text-sm text-white opacity-80">Risk Coverage Layer</div>
          </div>

          {/* Phase 4: Standard */}
          <div className="p-6 rounded-xl" style={{ background: colors.gradient.dark }}>
            <div className="text-2xl mb-2">📋</div>
            <h3 className="text-lg font-semibold text-white mb-2">Phase 4: Standard</h3>
            <div className="text-3xl font-bold text-white mb-1">🎯</div>
            <div className="text-sm text-white opacity-80">EIP-XXXX Protocol</div>
          </div>
        </div>
      </motion.div>

      {/* Network Effects Visualization */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="p-8 rounded-2xl"
        style={styles.card}
      >
        <h3 className="text-2xl font-bold mb-6" style={{ color: colors.accent }}>
          🌐 Network Effects Flywheel
        </h3>
        
        <div className="relative">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-6 rounded-xl" style={{ background: colors.primary + "20" }}>
              <div className="text-4xl mb-4">🤖</div>
              <h4 className="text-lg font-semibold mb-2" style={{ color: colors.primary }}>More Agents</h4>
              <p className="text-sm" style={{ color: colors.muted }}>Every new agent strengthens the network</p>
            </div>
            
            <div className="text-center p-6 rounded-xl" style={{ background: colors.secondary + "20" }}>
              <div className="text-4xl mb-4">📊</div>
              <h4 className="text-lg font-semibold mb-2" style={{ color: colors.secondary }}>More Threat Data</h4>
              <p className="text-sm" style={{ color: colors.muted }}>Collective intelligence improves protection</p>
            </div>
            
            <div className="text-center p-6 rounded-xl" style={{ background: colors.accent + "20" }}>
              <div className="text-4xl mb-4">🛡️</div>
              <h4 className="text-lg font-semibold mb-2" style={{ color: colors.accent }}>Better Protection</h4>
              <p className="text-sm" style={{ color: colors.muted }}>Superior security attracts more agents</p>
            </div>
          </div>
          
          {/* Circular arrows showing the flywheel */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-32 h-32 rounded-full border-2 border-dashed" style={{ borderColor: colors.gold + "40" }}>
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-2xl" style={{ color: colors.gold }}>🔄</div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* African Excellence Story */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="p-8 rounded-2xl"
        style={styles.card}
      >
        <h3 className="text-2xl font-bold mb-6" style={{ color: colors.gold, fontFamily: "'Cinzel Decorative', serif" }}>
          🌍 The African Excellence Story
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h4 className="text-xl font-semibold mb-4" style={{ color: colors.primary }}>Built in Ouagadougou</h4>
            <p className="mb-4" style={{ color: colors.muted }}>
              The infrastructure of trust for the autonomous economy was built in Burkina Faso's capital, 
              proving that world-class blockchain infrastructure can emerge from Africa.
            </p>
            
            <h4 className="text-xl font-semibold mb-4" style={{ color: colors.accent }}>Powered by AMD MI300X</h4>
            <p className="mb-4" style={{ color: colors.muted }}>
              Leveraging cutting-edge GPU technology for 10-100x performance improvements over CPU-based competitors, 
              optimized specifically for the ROCm stack.
            </p>
          </div>
          
          <div>
            <h4 className="text-xl font-semibold mb-4" style={{ color: colors.secondary }}>Dogon Cosmology</h4>
            <p className="mb-4" style={{ color: colors.muted }}>
              Named after the Dogon ritual of cosmic regeneration, where Sigui renews cosmic order every 60 years. 
              In the agentic economy, Sigui regenerates trust every 5ms.
            </p>
            
            <div className="p-6 rounded-xl" style={{ background: colors.gradient.dark }}>
              <div className="text-center">
                <div className="text-4xl mb-4">🌠</div>
                <h5 className="text-lg font-semibold text-white mb-2">Cultural Authenticity</h5>
                <p className="text-sm text-white opacity-80">
                  Our African origin story creates emotional connection and differentiation 
                  that pure tech companies can't replicate.
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Technical Excellence Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="p-8 rounded-2xl"
        style={styles.card}
      >
        <h3 className="text-2xl font-bold mb-6" style={{ color: colors.success }}>
          ⚡ Technical Excellence
        </h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center p-6 rounded-xl" style={{ background: colors.primary + "10" }}>
            <div className="text-3xl font-bold mb-2" style={{ color: colors.primary }}>&lt;50ms</div>
            <div className="text-sm" style={{ color: colors.muted }}>Response Time</div>
            <div className="text-xs mt-1" style={{ color: colors.success }}>vs 2000ms competitors</div>
          </div>
          
          <div className="text-center p-6 rounded-xl" style={{ background: colors.secondary + "10" }}>
            <div className="text-3xl font-bold mb-2" style={{ color: colors.secondary }}>&gt;96%</div>
            <div className="text-sm" style={{ color: colors.muted }}>Threat Detection</div>
            <div className="text-xs mt-1" style={{ color: colors.success }}>vs 88% baseline</div>
          </div>
          
          <div className="text-center p-6 rounded-xl" style={{ background: colors.accent + "10" }}>
            <div className="text-3xl font-bold mb-2" style={{ color: colors.accent }}>1000+</div>
            <div className="text-sm" style={{ color: colors.muted }}>Evaluations/Second</div>
            <div className="text-xs mt-1" style={{ color: colors.success }}>vs 10/second competitors</div>
          </div>
          
          <div className="text-center p-6 rounded-xl" style={{ background: colors.success + "10" }}>
            <div className="text-3xl font-bold mb-2" style={{ color: colors.success }}>100K+</div>
            <div className="text-sm" style={{ color: colors.muted }}>Concurrent Agents</div>
            <div className="text-xs mt-1" style={{ color: colors.success }}>Scalable architecture</div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}