import { Pool } from 'pg';

let pool;

export function getPool() {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      console.warn("DATABASE_URL environment variable is not defined. Database queries will return empty results.");
      return null;
    }
    pool = new Pool({
      connectionString,
      ssl: connectionString.includes('sslmode=require') || connectionString.includes('neon.tech') 
        ? { rejectUnauthorized: false } 
        : false
    });
  }
  return pool;
}

export async function query(text, params) {
  const activePool = getPool();
  if (!activePool) {
    return { rows: [] };
  }
  return activePool.query(text, params);
}
