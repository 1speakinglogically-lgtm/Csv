// quick-trade-sanity.mts
// Run: node --loader ts-node/esm quick-trade-sanity.mts <MINT_ADDRESS>
// Optional ENV: BIRDEYE_API_KEY=xxxx  (skips Birdeye checks if unset)

// pnpm add node-fetch
import fetch from "node-fetch";

const MINT = process.argv[2];
if(!MINT) throw new Error("Usage: node quick-trade-sanity.mts <MINT_ADDRESS>");

const BIRDEYE_KEY = process.env.BIRDEYE_API_KEY;

// 1) Birdeye trades: do we see sells?
async function hasRecentSells(mint:string){
  if(!BIRDEYE_KEY) return null;
  const url = `https://public-api.birdeye.so/defi/txs/token?address=${mint}&offset=0&limit=50`;
  const r = await fetch(url, { headers: { "x-api-key": BIRDEYE_KEY }});
  if(!r.ok) return null;
  const j:any = await r.json();
  if(!j?.data) return null;
  // Birdeye returns mixed txs; mark any that are sells (token -> SOL/USDC)
  const sells = j.data.filter((tx:any)=> String(tx.side || tx.type || "").toLowerCase().includes("sell")).length;
  const buys  = j.data.filter((tx:any)=> String(tx.side || tx.type || "").toLowerCase().includes("buy")).length;
  return { sells, buys, sample: j.data.slice(0,5).map((t:any)=>({side:t.side, amount:t.amount})) };
}

// 2) Jupiter quotes both directions (rough sniff for massive tax)
async function jupQuote(inputMint:string, outputMint:string, amount:number){ // amount in smallest units
  const url = `https://quote-api.jup.ag/v6/quote?inputMint=${inputMint}&outputMint=${outputMint}&amount=${amount}&slippageBps=50`;
  const r = await fetch(url);
  if(!r.ok) return null;
  const j:any = await r.json();
  if(!j?.data?.[0]) return null;
  return j.data[0]; // best route
}

const SOL = "So11111111111111111111111111111111111111112"; // wSOL

(async ()=>{
  const out:any = {};

  // A) Birdeye recent sells?
  out.birdeye = await hasRecentSells(MINT) || "Birdeye not checked (no API key or error)";

  // B) Jupiter quote round-trip sniff (buy then sell same notional)
  // Choose a tiny notional ~ $1: we'll use 0.005 SOL in lamports (adjust if SOL price shifts)
  const lamports = Math.floor(0.005 * 1e9);

  // SOL -> TOKEN
  const q1 = await jupQuote(SOL, MINT, lamports);
  if(q1){
    out.jup_buy_quote_outUnits = q1.outAmount; // token smallest units
    // TOKEN -> SOL for that outAmount
    const q2 = await jupQuote(MINT, SOL, Number(q1.outAmount));
    if(q2){
      const backToSol = Number(q2.outAmount) / 1e9;
      const startSol  = lamports / 1e9;
      const roundTripLossPct = ((startSol - backToSol)/startSol)*100;
      out.jup_roundtrip_loss_pct = Number(roundTripLossPct.toFixed(2));
      out.jup_note =
        roundTripLossPct > 20
          ? "⚠️ Huge round-trip loss → likely tax/illiquidity. Dust test BEFORE sizing up."
          : "✅ Round-trip quote looks reasonable for AMM spread.";
    } else {
      out.jup_note = "Could not fetch sell quote; token illiquid or path missing.";
    }
  } else {
    out.jup_note = "Could not fetch buy quote; token path missing.";
  }

  console.log(JSON.stringify(out, null, 2));
})().catch(e=>{ console.error(e); process.exit(1); });
