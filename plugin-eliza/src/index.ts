import { Plugin } from "@elizaos/core";
import { evaluateTransactionAction } from "./actions/evaluateTransaction";
import { threatProvider } from "./providers/threatProvider";

export const siguiPlugin: Plugin = {
    name: "sigui",
    description: "Sigui Protocol Plugin for ElizaOS. Provides real-time AI security oracle evaluations for blockchain transactions to prevent Drain Stars, Rug Pulls, and Mixer Chains.",
    actions: [evaluateTransactionAction],
    evaluators: [],
    providers: [threatProvider],
};

export default siguiPlugin;
