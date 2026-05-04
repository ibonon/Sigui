import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import { generateEntitySecretCiphertext } from "@circle-fin/developer-controlled-wallets";
import crypto from "node:crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_ENV = path.join(__dirname, "..", "..", ".env");

function loadEnv() {
  if (!fs.existsSync(ROOT_ENV)) return {};
  const content = fs.readFileSync(ROOT_ENV, "utf-8");
  const env = {};
  content.split("\n").forEach((line) => {
    const cleanedLine = line.replace(/\r/g, "");
    const match = cleanedLine.match(/^([^=]+)=(.*)$/);
    if (match) env[match[1].trim()] = match[2].trim();
  });
  return env;
}

async function main() {
  const args = process.argv.slice(2);
  const sourceWalletId = args[0];
  const destinationAddress = args[1];
  const amount = args[2];

  const env = loadEnv();
  const apiKey = env["CIRCLE_API_KEY"];
  const entitySecret = env["CIRCLE_ENTITY_SECRET"];

  try {
    // 1. USE THE OFFICIAL SDK FOR SECURITY ONLY! (To bypass Axios 'config' bug in Circle's wrapper)
    const entitySecretCiphertext = await generateEntitySecretCiphertext({ 
      apiKey, 
      entitySecret 
    });

    // 2. NATIVE HTTP FETCH FOR RELIABILITY
    const idempotencyKey = crypto.randomUUID();
    const payload = {
      idempotencyKey,
      walletId: sourceWalletId,
      destinationAddress: destinationAddress,
      amounts: [amount],
      tokenId: "15dc2b5d-0994-58b0-bf8c-3a0501148ee8", 
      feeLevel: "MEDIUM",
      entitySecretCiphertext
    };

    const res = await fetch("https://api.circle.com/v1/w3s/developer/transactions/transfer", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const body = await res.json();

    if (!res.ok) {
        console.log(JSON.stringify({ 
          status: "failed", 
          error: `HTTP ${res.status}: ` + JSON.stringify(body) 
        }));
        process.exit(1);
    }
    
    console.log(JSON.stringify({ 
      status: "complete", 
      txHash: body?.data?.id || body?.data?.txHash || `0xSDK_${sourceWalletId.substring(0,8)}`,
      data: body.data 
    }));

  } catch(e) {
    console.log(JSON.stringify({ 
      status: "failed", 
      error: String(e.stack || e) 
    }));
    process.exit(1);
  }
}

main();
