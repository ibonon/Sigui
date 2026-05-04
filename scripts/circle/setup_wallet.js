import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  registerEntitySecretCiphertext,
  initiateDeveloperControlledWalletsClient,
} from "@circle-fin/developer-controlled-wallets";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_ENV = path.join(__dirname, "..", "..", ".env");
const WALLET_SET_NAME = "ArcWarden Hackathon Wallet Set";

// Load .env manually to grab CIRCLE_API_KEY
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
  console.log(`[Env] Saving ${varName} to .env...`);
  // If exists, replace it, else append
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

  if (!apiKey || apiKey === "demo_key" || apiKey === "") {
    console.error("❌ ERREUR: Vous n'avez pas de CIRCLE_API_KEY valide dans votre fichier .env");
    console.error("Veuillez générer une clé sur https://console.circle.com et l'ajouter à la ligne CIRCLE_API_KEY=votre_clef dans le fichier .env");
    process.exit(1);
  }

  console.log("==========================================");
  console.log("🧙 ArcWarden - Création d'un Wallet Circle");
  console.log("==========================================\n");

  // 1. Register Entity Secret
  console.log("1. Génération de l'Entity Secret...");
  const entitySecret = crypto.randomBytes(32).toString("hex");
  
  try {
    await registerEntitySecretCiphertext({
      apiKey,
      entitySecret,
      recoveryFileDownloadPath: __dirname,
    });
    console.log("✅ Entity Secret enregistré et sauvegardé pour récupération.");
    appendEnvVars("CIRCLE_ENTITY_SECRET", entitySecret);
  } catch (err) {
    if (err.message && err.message.includes("already specified")) {
      console.log("⚠️ Un Entity secret existe déjà pour cette clé API, on continue avec si présent dans le .env...");
    } else {
      throw err;
    }
  }

  // Use the secret just created or the one from env if it failed to overwrite
  const activeEntitySecret = envVars["CIRCLE_ENTITY_SECRET"] || entitySecret;

  // 2. Client init
  console.log("\n2. Connexion au client Circle...");
  const client = initiateDeveloperControlledWalletsClient({ 
    apiKey, 
    entitySecret: activeEntitySecret 
  });

  // 3. Create wallet set
  console.log("3. Création du Wallet Set...");
  let walletSetId = envVars["ARCWARDEN_WALLET_SET_ID"];
  if (!walletSetId) {
    const wsRes = await client.createWalletSet({ name: WALLET_SET_NAME });
    walletSetId = wsRes.data?.walletSet?.id;
    if (!walletSetId) throw new Error("Échec de la création du Wallet Set.");
    appendEnvVars("ARCWARDEN_WALLET_SET_ID", walletSetId);
  }
  console.log(`✅ Wallet Set ID = ${walletSetId}`);

  // 4. Create Wallet
  console.log("\n4. Création du Wallet sur ARC-TESTNET...");
  const wRes = await client.createWallets({
    walletSetId: walletSetId,
    blockchains: ["ARC-TESTNET"],
    count: 1,
    accountType: "EOA",
  });

  const wallet = wRes.data?.wallets?.[0];
  if (!wallet) throw new Error("Échec de la création du Wallet Arc.");

  console.log(`✅ Wallet ID = ${wallet.id}`);
  console.log(`✅ Adresse   = ${wallet.address}`);

  appendEnvVars("ARCWARDEN_WALLET_ID", wallet.id);
  appendEnvVars("ARCWARDEN_WALLET_ADDRESS", wallet.address);

  // Overwrite demo mode if present so it activates real mode!
  appendEnvVars("DEMO_MODE", "false");

  console.log("\n==========================================");
  console.log("🎉 SUCCÈS ! Votre fichier .env a été rempli automatiquement !");
  console.log("👉 Étape suivante : Rendez-vous sur https://faucet.circle.com");
  console.log(`   Réseau  : Arc Testnet`);
  console.log(`   Adresse : ${wallet.address}`);
  console.log("   Faites 'Send USDC' pour obtenir des fonds de test.");
  console.log("==========================================");
}

main().catch((err) => {
  console.error("❌ Erreur inattendue:", err.response?.data || err.message || err);
});
