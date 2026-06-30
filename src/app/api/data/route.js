import { NextResponse } from 'next/server';
import { query } from '../../lib/db';

const ALL_CATEGORIES = [
  "rent", "food", "groceries", "travel", "bills", "emis", "insurance",
  "investments", "emergency", "clothes", "luxuries", "health", "education", "other"
];

export async function GET() {
  try {
    // Fetch all transactions
    const txnsResult = await query("SELECT id, date, category, amount, note, type FROM txns ORDER BY date ASC, id ASC");
    
    // Fetch configuration
    let config = {
      currency: "₹",
      monthlyBudget: 0,
      budgets: {},
      categories: ALL_CATEGORIES
    };
    
    const configResult = await query("SELECT value FROM config WHERE key = $1", ["config"]);
    if (configResult.rows.length > 0) {
      try {
        const dbConfig = JSON.parse(configResult.rows[0].value);
        config = { ...config, ...dbConfig };
      } catch (e) {
        console.error("Failed to parse config from DB:", e);
      }
    }
    
    return NextResponse.json({
      transactions: txnsResult.rows,
      config: config
    });
  } catch (error) {
    console.error("Error in GET /api/data:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
