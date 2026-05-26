// ─── Sigui Protocol — Landing Page Data ────────────────────────────────────

export const capabilities = [
  {
    id: "network",
    tag: "Network",
    title: "Oracle Décentralisé",
    description: "Un réseau mondial de validateurs qui inspectent les transactions IA avec une latence < 50ms. Le trafic est routé dynamiquement vers les nœuds les plus performants.",
    icon: "🌐",
    features: ["Routing dynamique", "Haute disponibilité", "No single point of failure"]
  },
  {
    id: "security",
    tag: "Security",
    title: "Pipeline de Risque en 5 Couches",
    description: "Inspection multimodale (visuelle, sémantique, réputationnelle) avant toute exécution. Chaque verdict produit une preuve ZK-STARK infalsifiable.",
    icon: "🛡️",
    features: ["Imina-Na V2 (Visuel)", "Analyse sémantique LLM", "Preuves ZK-STARK"]
  },
  {
    id: "marketplace",
    tag: "Marketplace",
    title: "Modèles & Datasets Open-Source",
    description: "Accédez aux meilleurs modèles de détection (Trustformer) et aux datasets d'attaques IA mis à jour par la communauté. Monétisez vos propres règles de sécurité.",
    icon: "🛒",
    features: ["1M+ images d'attaques", "Modèles Hugging Face", "Monétisation de règles"]
  },
  {
    id: "wallet",
    tag: "Wallet",
    title: "Micro-Paiements x402",
    description: "Modèle économique natif pay-per-inspection. À $0.001 par transaction via des canaux d'état L2, la sécurité devient transparente pour vos agents.",
    icon: "💸",
    features: ["Paiements L2 (Starknet)", "Protocole HTTP 402", "Facturation fractionnée"]
  },
  {
    id: "systemlogs",
    tag: "System Logs",
    title: "Télémétrie & Auditabilité",
    description: "Chaque action de votre agent est logguée cryptographiquement. Un dashboard temps réel permet de rejouer et d'analyser les vecteurs d'attaque bloqués.",
    icon: "🖥️",
    features: ["Streaming temps réel", "Export immuable", "Alertes webhook"]
  },
  {
    id: "research",
    tag: "Research",
    title: "Trustformer : La Génération Suivante",
    description: "Architecture IA native qui élimine le rendu PNG pour l'inspection visuelle. Traitement direct du DOM avec attention pondérée par la réputation.",
    icon: "🔬",
    features: ["Latence cible < 5ms", "Traitement DOM natif", "Preprint arXiv"]
  },
  {
    id: "swarm",
    tag: "Swarm",
    title: "Déploiements Multi-Agents",
    description: "Intégration transparente avec LangGraph, CrewAI et AutoGen. Sécurisez des flottes entières d'agents qui communiquent entre eux.",
    icon: "🐝",
    features: ["Inspection inter-agents", "Politiques de groupe", "SDK Python unifié"]
  },
  {
    id: "identity",
    tag: "Identity",
    title: "Standard ERC-8259",
    description: "Identité et réputation on-chain pour agents autonomes. Chaque agent possède une adresse vérifiable et construit sa confiance au fil des transactions.",
    icon: "🆔",
    features: ["Réputation persistante", "Révocation instantanée", "Interopérabilité Web3"]
  }
];

export const sahelionStack = [
  { level: "Couche 1", name: "Réseau", tech: "NexusMind P2P Mesh", desc: "Topologie décentralisée, DHT Kademlia, propagation en temps réel." },
  { level: "Couche 2", name: "Sécurité", tech: "Sigui Protocol + ERC-8259", desc: "Orchestration des verdicts, consensus, et réputation on-chain." },
  { level: "Couche 3", name: "Intelligence", tech: "Imina-Na V2 + Trustformer", desc: "Détection visuelle et sémantique des menaces IA, latence < 5ms." },
  { level: "Couche 4", name: "SDK", tech: "pip install sigui-sdk", desc: "Décorateur Python universel pour agents LangGraph, CrewAI, AutoGen." },
  { level: "Couche 5", name: "Standard", tech: "ERC-8259", desc: "Interopérabilité Web3, preuve de réputation et d'identité agentique." },
];

export const operatorVision = [
  "N'importe quel opérateur installe NexusMind",
  "Son nœud rejoint le réseau P2P",
  "Il fait tourner Trustformer localement",
  "Il évalue des transactions d'agents IA",
  "Il gagne des USDC par évaluation",
  "Sa réputation s'accumule via ERC-8259",
  "Il devient un nœud de confiance de l'économie agentique"
];

export const metrics = [
  { value: "1M+", label: "Images dans le dataset", sub: "Dataset Imina-Na" },
  { value: "92.9%", label: "F1-Score", sub: "Détection visuelle" },
  { value: "<50ms", label: "Latence d'inspection", sub: "Par transaction" },
  { value: "380+", label: "Attaques enregistrées", sub: "Base de menaces" },
];

export const integrations = [
  { name: "LangGraph", category: "framework" },
  { name: "CrewAI", category: "framework" },
  { name: "AutoGen", category: "framework" },
  { name: "LangChain", category: "framework" },
  { name: "elizaOS", category: "framework" },
  { name: "Ethereum", category: "chain" },
  { name: "Starknet", category: "chain" },
  { name: "Aptos", category: "chain" },
  { name: "Arbitrum", category: "chain" },
  { name: "Polygon", category: "chain" },
  { name: "AMD MI300X", category: "hardware" },
  { name: "ROCm 7.0", category: "hardware" },
];

export const architectureSteps = [
  { id: 1, label: "Agent Transaction", icon: "🤖", desc: "Requête sortante de l'agent IA" },
  { id: 2, label: "Risk Pipeline", icon: "🔍", desc: "5 couches d'analyse parallèle" },
  { id: 3, label: "Imina-Na V2", icon: "🧠", desc: "Inspection visuelle multimodale" },
  { id: 4, label: "ZK Proof", icon: "🔐", desc: "Génération de preuve cryptographique" },
  { id: 5, label: "Verdict", icon: "✅", desc: "Approve / Block + preuve on-chain" },
];

export const codeExample = `from sigui import Warden

warden = Warden(api_key="sk-...")

@warden.inspect
async def my_agent_task(url: str) -> str:
    # Votre logique d'agent ici
    return await browser.navigate(url)`;

export const navLinks = [
  { label: "Docs", href: "https://github.com/ibonon/sigui-sdk" },
  { label: "GitHub", href: "https://github.com/ibonon/Sigui" },
  { label: "Hugging Face", href: "https://huggingface.co/datasets/ibonon/imina-na" },
  { label: "arXiv", href: "#trustformer" },
];

export const footerLinks = [
  { label: "GitHub", href: "https://github.com/ibonon/Sigui" },
  { label: "Hugging Face", href: "https://huggingface.co/datasets/ibonon/imina-na" },
  { label: "PyPI", href: "https://pypi.org/project/sigui-sdk/" },
  { label: "arXiv", href: "#trustformer" },
  { label: "X / Twitter", href: "https://x.com/siguiprotocol" },
];
