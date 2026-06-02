/**
 * Sigui v3.0 — GrayZone Wallet Setup
 * Creates the missing GrayZone agent Circle DCW wallet on ARC-TESTNET
 * and patches it directly into the .env file.
 *
 * Usage (Node 20+):
 *   node --env-file=.env scripts/circle/setup_grayzone_wallet.js
 *
 * Prerequisites in .env:
 *   CIRCLE_API_KEY
 *   CIRCLE_ENTITY_SECRET
 *   SIGUI_WALLET_SET_ID
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { initiateDeveloperControlledWalletsClient } from "@circle-fin/developer-controlled-wallets";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_ENV = path.resolve(__dirname, "..", "..", ".env");

// ── Patch a key=value line in the .env file ──────────────────────────────────

function patchEnv(key, value) {
  let content = fs.existsSync(ROOT_ENV)
    ? fs.readFileSync(ROOT_ENV, "utf-8")
    : "";

  const regex = new RegExp(`^${key}=.*$`, "m");
  if (regex.test(content)) {
    content = content.replace(regex, `${key}=${value}`);
  } else {
    if (content.length > 0 && !content.endsWith("\n")) content += "\n";
    content += `${key}=${value}\n`;
  }

  fs.writeFileSync(ROOT_ENV, content, "utf-8");
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  // Read credentials from process.env (loaded via --env-file=.env)
  const apiKey = process.env.CIRCLE_API_KEY;
  const entitySecret = process.env.CIRCLE_ENTITY_SECRET;
  const walletSetId = process.env.SIGUI_WALLET_SET_ID;
  const existingId = process.env.GRAYZONE_WALLET_ID;

  // ── Validation ──────────────────────────────────────────────────────────────
  if (!apiKey || apiKey === "demo_key") {
    console.error("❌ CIRCLE_API_KEY is missing or still set to 'demo_key'.");
    console.error(
      "   Make sure you run: node --env-file=.env scripts/circle/setup_grayzone_wallet.js",
    );
    process.exit(1);
  }
  if (!entitySecret) {
    console.error("❌ CIRCLE_ENTITY_SECRET is missing in .env.");
    console.error(
      "   Get it from: https://developers.circle.com/w3s/circle-developer-account",
    );
    process.exit(1);
  }
  if (!walletSetId) {
    console.error("❌ SIGUI_WALLET_SET_ID is missing in .env.");
    console.error(
      "   Create a wallet set in the Circle Console and add it to .env.",
    );
    process.exit(1);
  }

  // ── Already configured? ─────────────────────────────────────────────────────
  if (existingId && existingId !== "demo_grayzone_wallet_id") {
    console.warn("⚠️  GRAYZONE_WALLET_ID is already configured:", existingId);
    console.warn("   Remove it from .env if you want to recreate it.");
    process.exit(0);
  }

  console.log("==============================================");
  console.log("🧙 Sigui — GrayZone Wallet Creation");
  console.log("==============================================");
  console.log();

  // ── Circle client ───────────────────────────────────────────────────────────
  const client = initiateDeveloperControlledWalletsClient({
    apiKey,
    entitySecret,
  });

  // ── Create wallet ───────────────────────────────────────────────────────────
  console.log("Creating GrayZone EOA wallet on ARC-TESTNET…");

  let wallet;
  try {
    const res = await client.createWallets({
      walletSetId,
      blockchains: ["ARC-TESTNET"],
      count: 1,
      accountType: "EOA",
    });
    wallet = res.data?.wallets?.[0];
  } catch (err) {
    console.error(
      "❌ Circle API error:",
      err?.response?.data ?? err?.message ?? err,
    );
    process.exit(1);
  }

  if (!wallet) {
    console.error(
      "❌ Wallet creation returned empty response.",
      "Check your API key and wallet set ID.",
    );
    process.exit(1);
  }

  // ── Patch .env ──────────────────────────────────────────────────────────────
  patchEnv("GRAYZONE_WALLET_ID", wallet.id);
  patchEnv("GRAYZONE_WALLET_ADDRESS", wallet.address);

  // ── Success ─────────────────────────────────────────────────────────────────
  console.log();
  console.log("✅ GrayZone Wallet ID      =", wallet.id);
  console.log("✅ GrayZone Wallet Address =", wallet.address);
  console.log();
  console.log("==============================================");
  console.log("🎉 Done! .env updated with GrayZone wallet.");
  console.log();
  console.log("👉 Next — fund this wallet with testnet USDC:");
  console.log("   https://faucet.circle.com");
  console.log();
  console.log("   Address to fund:", wallet.address);
  console.log("   Network        : Arc Testnet");
  console.log("   Amount         : 10–20 USDC recommended");
  console.log();
  console.log(
    "   Then restart Sigui — GrayZone will activate automatically.",
  );
  console.log("==============================================");
}

main().catch((err) => {
  console.error(
    "❌ Unexpected error:",
    err?.response?.data ?? err?.message ?? err,
  );
  process.exit(1);
});
