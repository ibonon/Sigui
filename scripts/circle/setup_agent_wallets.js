import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  initiateDeveloperControlledWalletsClient,
} from "@circle-fin/developer-controlled-wallets";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_ENV = path.join(__dirname, "..", "..", ".env");

function loadEnv() {
  if (!fs.existsSync(ROOT_ENV)) return {};
  const content = fs.readFileSync(ROOT_ENV, "utf-8");
  const env = {};
  content.split("\n").forEach((line) => {
    const match = line.match(/^([^=]+)=(.*)$/);
    if (match) env[match[1].trim()] = match[2].trim();
  });
  return env;
}

const appendEnvVars = (varName, value) => {
  let content = fs.existsSync(ROOT_ENV) ? fs.readFileSync(ROOT_ENV, "utf-8") : "";
  const regex = new RegExp(`^${varName}=.*$`, "m");
  if (regex.test(content)) {
    content = content.replace(regex, `${varName}=${value}`);
  } else {
    if (!content.endsWith("\n") && content.length > 0) content += "\n";
    content += `${varName}=${value}\n`;
  }
  fs.writeFileSync(ROOT_ENV, content, "utf-8");
};

async function main() {
  const envVars = loadEnv();
  const apiKey = envVars["CIRCLE_API_KEY"];
  const entitySecret = envVars["CIRCLE_ENTITY_SECRET"];
  const walletSetId = envVars["SIGUI_WALLET_SET_ID"];

  if (!apiKey || !entitySecret || !walletSetId) {
    console.error("❌ ERREUR: Il manque CIRCLE_API_KEY, CIRCLE_ENTITY_SECRET ou SIGUI_WALLET_SET_ID dans le .env!");
    process.exit(1);
  }

  console.log("==========================================");
  console.log("🧙 Sigui - Création de 4 Wallets Live");
  console.log("==========================================\n");

  const client = initiateDeveloperControlledWalletsClient({ 
    apiKey, 
    entitySecret
  });

  const generateAgent = async (prefix) => {
    console.log(`Création du wallet pour : ${prefix.toUpperCase()}...`);
    const wRes = await client.createWallets({
      walletSetId: walletSetId,
      blockchains: ["ARC-TESTNET"],
      count: 1,
      accountType: "EOA",
    });
    const wallet = wRes.data?.wallets?.[0];
    if (!wallet) throw new Error(`Échec de la création du Wallet pour ${prefix}`);

    appendEnvVars(`${prefix}_WALLET_ID`, wallet.id);
    appendEnvVars(`${prefix}_WALLET_ADDRESS`, wallet.address);
    console.log(`✅ ${prefix.toUpperCase()} Wallet ID = ${wallet.id}`);
    console.log(`✅ ${prefix.toUpperCase()} Adresse   = ${wallet.address}\n`);
  };

  await generateAgent("PAYER");
  await generateAgent("ATTACKER");
  await generateAgent("MONITOR");
  await generateAgent("LEARNER");

  console.log("==========================================");
  console.log("🎉 SUCCÈS ! Vos 4 faux agents ont maintenant de VRAIS portefeuilles blockchain.");
  console.log("👉 Étape Suivante (OBLIGATOIRE !) :");
  console.log("   Récupérez ces adresses dans le fichier .env et");
  console.log("   allez sur https://faucet.circle.com pour donner de l'USDC Testnet");
  console.log("   à CHACUN de ces 4 portefeuilles avant de lancer την API !");
  console.log("==========================================");
}

main().catch((err) => {
  console.error("❌ Erreur inattendue:", err.response?.data || err.message || err);
});
