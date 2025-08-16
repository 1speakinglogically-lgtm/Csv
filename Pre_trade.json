// preflight-check.mts
// Run: node --loader ts-node/esm preflight-check.mts <MINT_ADDRESS>
// ENV: RPC_URL="https://api.mainnet-beta.solana.com" (or your RPC)

// pnpm add @solana/web3.js @solana/spl-token
import {Connection, PublicKey} from "@solana/web3.js";
import {
  getMint,
  TOKEN_PROGRAM_ID,
  TOKEN_2022_PROGRAM_ID,
  type Mint,
} from "@solana/spl-token";

const RPC_URL = process.env.RPC_URL || "https://api.mainnet-beta.solana.com";

function pct(n:number){ return (n*100).toFixed(2)+"%"; }

async function getProgramIdForMint(conn: Connection, mintPk: PublicKey){
  const acct = await conn.getAccountInfo(mintPk);
  if(!acct) throw new Error("Mint account not found");
  return acct.owner;
}

async function checkAuthorities(conn: Connection, mintPk: PublicKey, programId: PublicKey){
  const mint: Mint = await getMint(conn, mintPk, "confirmed", programId);
  const freeze = mint.freezeAuthority ?? null;
  const mintAuth = mint.mintAuthority ?? null;
  return {
    supply: Number(mint.supply),
    decimals: mint.decimals,
    freezeAuthority: freeze ? freeze.toBase58() : null,
    mintAuthority: mintAuth ? mintAuth.toBase58() : null,
  };
}

async function detectToken2022TransferFee(conn: Connection, mintPk: PublicKey, programId: PublicKey){
  // If it’s not a Token-2022 mint, there can’t be a Token-2022 transfer fee extension.
  if (!programId.equals(TOKEN_2022_PROGRAM_ID)) return null;

  // @solana/spl-token encodes extensions in the mint account data.
  // We can parse them from the raw data; newer versions expose helpers, but we’ll keep this generic:
  const acct = await conn.getAccountInfo(mintPk);
  if(!acct) return null;

  // Simple heuristic: if data is long enough to include extensions and the owner is TOKEN_2022,
  // spl-token tooling will parse transfer fee via getMint; here we just surface that it’s Token-2022.
  // (If you upgrade spl-token, you can import and call getTransferFeeConfig(mint) here.)
  return { hasToken2022Extensions: true }; // presence flag; treat as “possible tax”, verify with dust trade
}

async function topHolderConcentration(conn: Connection, mintPk: PublicKey){
  const largest = await conn.getTokenLargestAccounts(mintPk);
  const top10 = largest.value.slice(0,10);
  const uiAmounts = top10.map(a => Number(a.uiAmount || 0));
  const top10Sum = uiAmounts.reduce((a,b)=>a+b,0);

  // Get total supply via getMint
  const programId = await getProgramIdForMint(conn, mintPk);
  const mint = await getMint(conn, mintPk, "confirmed", programId);
  const totalSupply = Number(mint.supply) / 10**mint.decimals;

  const concentration = totalSupply > 0 ? (top10Sum / totalSupply) : 0;
  return { top10Pct: concentration, totalSupply, decimals: mint.decimals };
}

async function main(){
  const mintStr = process.argv[2];
  if(!mintStr) throw new Error("Usage: node preflight-check.mts <MINT_ADDRESS>");

  const conn = new Connection(RPC_URL, "confirmed");
  const mintPk = new PublicKey(mintStr);

  const programId = await getProgramIdForMint(conn, mintPk);
  const prog =
    programId.equals(TOKEN_PROGRAM_ID) ? "SPL Token (Tokenkeg)" :
    programId.equals(TOKEN_2022_PROGRAM_ID) ? "SPL Token-2022 (Tokenz)" :
    `Custom program: ${programId.toBase58()}`;

  const authorities = await checkAuthorities(conn, mintPk, programId);
  const t22 = await detectToken2022TransferFee(conn, mintPk, programId);
  const holders = await topHolderConcentration(conn, mintPk);

  // Heuristic flags
  const flags:string[] = [];
  if (authorities.freezeAuthority) flags.push("Freeze authority present (rug lever)");
  if (authorities.mintAuthority)   flags.push("Mint authority present (can mint more)");
  if (t22)                         flags.push("Token-2022 mint (possible transfer-fee/tax; dust test recommended)");
  if (holders.top10Pct > 0.20)     flags.push(`High holder concentration (${pct(holders.top10Pct)})`);

  console.log(JSON.stringify({
    mint: mintPk.toBase58(),
    program: prog,
    supply: holders.totalSupply,
    decimals: holders.decimals,
    authorities,
    top10_concentration_pct: Number((holders.top10Pct*100).toFixed(2)),
    flags,
    verdict: flags.length ? "⚠️ Risky / proceed with caution" : "✅ Basic on-chain checks OK",
  }, null, 2));
}

main().catch(e=>{ console.error(e); process.exit(1); });
