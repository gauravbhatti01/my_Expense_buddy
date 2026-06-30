import { NextResponse } from 'next/server';
import { query } from '../../lib/db';

export async function POST(request) {
  try {
    const data = await request.json();
    
    // Fetch current config
    let config = {
      currency: "₹",
      monthlyBudget: 0,
      budgets: {}
    };
    
    const configResult = await query("SELECT value FROM config WHERE key = $1", ["config"]);
    if (configResult.rows.length > 0) {
      try {
        config = JSON.parse(configResult.rows[0].value);
      } catch (e) {
        console.error("Failed to parse config from DB:", e);
      }
    }
    
    // Update config fields
    config.monthlyBudget = parseFloat(data.monthlyBudget) || 0;
    config.budgets = data.budgets || {};
    
    // Save updated config to PostgreSQL via Upsert
    await query(
      `INSERT INTO config (key, value) VALUES ($1, $2)
       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value`,
      ["config", JSON.stringify(config)]
    );
    
    return NextResponse.json({
      status: "success",
      config: config
    });
  } catch (error) {
    console.error("Error in POST /api/config:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
