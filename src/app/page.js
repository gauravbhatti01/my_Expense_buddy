// Force Vercel redeploy
'use client';

import { useState, useEffect } from 'react';

const CATEGORY_DISPLAY_NAMES = {
  rent: "🏠 Rent",
  food: "🍛 Food",
  groceries: "🛒 Groceries",
  travel: "🚇 Travel",
  bills: "💡 Bills & Recharge",
  emis: "💳 EMIs (Bike + HDFC)",
  insurance: "🛡️ Insurance",
  investments: "📈 SIP / Investments",
  emergency: "🚑 Emergency Fund",
  clothes: "👕 Shopping / Clothes",
  luxuries: "🎉 Entertainment / Luxuries",
  health: "💪 Health",
  education: "📚 Education / Learning",
  other: "📦 Other / Buffer"
};

const CATEGORY_COLORS = {
  rent: "#a78bfa",
  food: "#fb923c",
  groceries: "#34d399",
  travel: "#38bdf8",
  bills: "#fbbf24",
  emis: "#c084fc",
  insurance: "#f97316",
  investments: "#22d3ee",
  emergency: "#f43f5e",
  clothes: "#f472b6",
  luxuries: "#f87171",
  health: "#4ade80",
  education: "#facc15",
  other: "#9ca3af"
};

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [config, setConfig] = useState({
    currency: "₹",
    monthlyBudget: 0,
    budgets: {},
    categories: []
  });
  const [selectedMonth, setSelectedMonth] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formMonthlyBudget, setFormMonthlyBudget] = useState(0);
  const [formBudgets, setFormBudgets] = useState({});
  const [showToast, setShowToast] = useState(false);

  const fetchData = async () => {
    try {
      const res = await fetch('/api/data');
      if (!res.ok) throw new Error('Failed to load data');
      const result = await res.json();
      setTransactions(result.transactions || []);
      setConfig(result.config || {});
      
      // Derive months from transactions
      const months = Array.from(new Set((result.transactions || []).map(r => r.date.slice(0, 7)))).sort();
      if (months.length > 0) {
        setSelectedMonth(prev => prev || months[months.length - 1]);
      } else {
        const now = new Date();
        const curMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        setSelectedMonth(prev => prev || curMonth);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openSettings = () => {
    setFormMonthlyBudget(config.monthlyBudget || 0);
    setFormBudgets(config.budgets || {});
    setIsModalOpen(true);
  };

  const saveSettings = async () => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          monthlyBudget: formMonthlyBudget,
          budgets: formBudgets
        })
      });
      if (!res.ok) throw new Error('Server error');
      const result = await res.json();
      setConfig(result.config);
      setIsModalOpen(false);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    } catch (err) {
      alert("Failed to save budgets: " + err.message);
    }
  };

  // Helper: Format Money in Indian Digit Grouping style (e.g. 12,34,567)
  const fmtINR = (val, withSymbol = true) => {
    const value = Math.round(val || 0);
    const neg = value < 0;
    const s = String(Math.abs(value));
    let result;
    if (s.length <= 3) {
      result = s;
    } else {
      const last3 = s.slice(-3);
      let rest = s.slice(0, -3);
      const parts = [];
      while (rest.length > 2) {
        parts.unshift(rest.slice(-2));
        rest = rest.slice(0, -2);
      }
      if (rest) parts.unshift(rest);
      result = parts.join(",") + "," + last3;
    }
    return (neg ? "-" : "") + (withSymbol ? config.currency : "") + result;
  };

  const monthLabel = (key) => {
    if (!key) return "—";
    const parts = key.split("-");
    const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    return names[parseInt(parts[1], 10) - 1] + " " + parts[0];
  };

  const daysInMonth = (key) => {
    if (!key) return 30;
    const parts = key.split("-").map(Number);
    return new Date(parts[0], parts[1], 0).getDate();
  };

  // Filter and Aggregates
  const currentMonthTxns = transactions.filter(r => r.date.slice(0, 7) === selectedMonth);
  const currentMonthExpenses = currentMonthTxns.filter(r => r.type === 'expense');
  
  const categoryTotals = currentMonthExpenses.reduce((acc, r) => {
    acc[r.category] = (acc[r.category] || 0) + r.amount;
    return acc;
  }, {});

  const totalSpent = Object.values(categoryTotals).reduce((sum, val) => sum + val, 0);
  const budgetLimit = config.monthlyBudget || 0;
  const remainingBudget = budgetLimit - totalSpent;
  const budgetPercentage = budgetLimit > 0 ? (totalSpent / budgetLimit) * 100 : 0;

  const today = new Date();
  const currentYearMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
  const isCurrentMonth = selectedMonth === currentYearMonth;
  const daysTotal = daysInMonth(selectedMonth);
  const dayOfMonth = isCurrentMonth ? today.getDate() : daysTotal;
  const projectedSpend = dayOfMonth > 0 ? (totalSpent / dayOfMonth) * daysTotal : totalSpent;

  // Month options
  const allMonths = Array.from(new Set(transactions.map(r => r.date.slice(0, 7)))).sort();
  if (allMonths.length === 0 && selectedMonth) {
    allMonths.push(selectedMonth);
  }

  // --- SVG Charts Calculations ---
  
  // 1. Donut Chart Slices
  const donutR = 58;
  const donutCircumference = 2 * Math.PI * donutR;
  const sortedCategories = Object.keys(categoryTotals).sort((a, b) => categoryTotals[b] - categoryTotals[a]);
  let donutOffset = 0;

  // 2. Daily Burn Line Chart
  const burnW = 420;
  const burnH = 190;
  const padL = 42;
  const padR = 14;
  const padT = 14;
  const padB = 24;
  const plotW = burnW - padL - padR;
  const plotH = burnH - padT - padB;

  const dailyAmounts = {};
  currentMonthExpenses.forEach(r => {
    const day = parseInt(r.date.slice(8, 10), 10);
    dailyAmounts[day] = (dailyAmounts[day] || 0) + r.amount;
  });

  const dailyPoints = [];
  let cumSpend = 0;
  const lastDayToPlot = isCurrentMonth ? today.getDate() : daysTotal;
  for (let d = 1; d <= daysTotal; d++) {
    if (d <= lastDayToPlot) cumSpend += (dailyAmounts[d] || 0);
    dailyPoints.push(cumSpend);
  }
  const maxValBurn = Math.max(budgetLimit, cumSpend, 1);

  const burnX = (day) => padL + (plotW * (day - 1) / (daysTotal - 1 || 1));
  const burnY = (val) => padT + plotH - (plotH * val / maxValBurn);

  // Path for cumulative spending
  let burnLinePath = "";
  let burnAreaPath = "";
  if (lastDayToPlot > 0) {
    burnLinePath = `M ${burnX(1)} ${burnY(dailyPoints[0])}`;
    for (let i = 1; i < lastDayToPlot; i++) {
      burnLinePath += ` L ${burnX(i + 1)} ${burnY(dailyPoints[i])}`;
    }
    burnAreaPath = `${burnLinePath} L ${burnX(lastDayToPlot)} ${burnY(0)} L ${burnX(1)} ${burnY(0)} Z`;
  }

  // Pace line path
  const paceLinePath = `M ${burnX(1)} ${burnY(0)} L ${burnX(daysTotal)} ${burnY(budgetLimit)}`;

  // 3. Month Over Month Bars
  const momMonthsSet = new Set(transactions.map(r => r.date.slice(0, 7)));
  const momAllMonths = Array.from(momMonthsSet).sort();
  const selectedIdx = momAllMonths.indexOf(selectedMonth);
  const startIdx = Math.max(0, selectedIdx - 5);
  const window6Months = momAllMonths.slice(startIdx, selectedIdx + 1);
  while (window6Months.length < 6) {
    window6Months.unshift(null);
  }

  const window6Totals = window6Months.map(m => {
    if (!m) return 0;
    return transactions
      .filter(r => r.date.slice(0, 7) === m && r.type === 'expense')
      .reduce((sum, r) => sum + r.amount, 0);
  });
  const maxValMoM = Math.max(...window6Totals, 1);

  const momW = 1000;
  const momH = 160;
  const momPadB = 28;
  const momPadT = 10;
  const momSlot = momW / 6;
  const momBarW = momSlot * 0.46;

  // --- Insights Logic ---
  const generateInsights = () => {
    const list = [];
    if (totalSpent === 0) {
      list.push({ text: "No spending logged yet this month — text the bot to get started.", tone: null });
      return list;
    }

    // 1. Biggest Category
    if (sortedCategories.length > 0) {
      const biggest = sortedCategories[0];
      const annualSaving = categoryTotals[biggest] * 0.2 * 12;
      list.push({
        text: `Biggest category is <b>${biggest}</b> at ${fmtINR(categoryTotals[biggest])}. Cutting it by 20% would save <b>${fmtINR(annualSaving)}</b> a year.`,
        tone: null
      });
    }

    // 2. Discretionary spend
    const discretionary = (categoryTotals.food || 0) + (categoryTotals.luxuries || 0) + (categoryTotals.clothes || 0);
    const discPct = totalSpent > 0 ? (discretionary / totalSpent) * 100 : 0;
    list.push({
      text: `Discretionary spend (food + luxuries + clothes) is <b>${fmtINR(discretionary)}</b> — ${discPct.toFixed(0)}% of this month's total.`,
      tone: discPct > 45 ? "bad" : null
    });

    // 3. Food order frequency
    const foodTxns = currentMonthExpenses.filter(r => r.category === "food");
    const weeksElapsed = Math.max(1, Math.ceil(today.getDate() / 7));
    const perWeek = (foodTxns.length / weeksElapsed).toFixed(1);
    list.push({
      text: `Logged <b>${foodTxns.length}</b> food orders this month — roughly <b>${perWeek}/week</b>.`,
      tone: null
    });

    // 4. Over cap alerts
    const overCats = Object.keys(config.budgets || {}).filter(c => (categoryTotals[c] || 0) > (config.budgets[c] || 0));
    if (overCats.length > 0) {
      list.push({
        text: `Over cap in <b>${overCats.length}</b> ${overCats.length === 1 ? "category" : "categories"}: ${overCats.join(", ")}.`,
        tone: "bad"
      });
    } else {
      list.push({ text: "No category has crossed its budget cap yet.", tone: "good" });
    }

    // 5. MoM changes
    const prevMonth = selectedIdx > 0 ? momAllMonths[selectedIdx - 1] : null;
    if (prevMonth) {
      const prevTotal = transactions
        .filter(r => r.date.slice(0, 7) === prevMonth && r.type === 'expense')
        .reduce((sum, r) => sum + r.amount, 0);
      if (prevTotal > 0) {
        const change = ((totalSpent - prevTotal) / prevTotal) * 100;
        const tone = change > 0 ? "bad" : "good";
        list.push({
          text: `Spending is <b>${change >= 0 ? "up" : "down"} ${Math.abs(change).toFixed(0)}%</b> vs ${monthLabel(prevMonth)} (${fmtINR(prevTotal)} → ${fmtINR(totalSpent)}).`,
          tone: tone
        });
      }
    }

    // 6. Pace
    if (budgetLimit > 0) {
      if (projectedSpend <= budgetLimit) {
        list.push({
          text: `On pace to finish <b>${fmtINR(budgetLimit - projectedSpend)} under budget</b> at the current rate.`,
          tone: "good"
        });
      } else {
        list.push({
          text: `At the current pace, projected to land <b>${fmtINR(projectedSpend - budgetLimit)} over budget</b>.`,
          tone: "bad"
        });
      }
    }

    return list;
  };

  const insights = generateInsights();

  if (loading) {
    return (
      <div className="wrap" style={{ textAlign: 'center', marginTop: '100px', fontSize: '18px', color: 'var(--muted)' }}>
        Loading Ledger Database...
      </div>
    );
  }

  return (
    <div className="wrap">
      {/* SUCCESS TOAST */}
      <div className="success-toast" style={{ display: showToast ? 'block' : 'none' }}>
        ✓ Budgets updated successfully
      </div>

      {/* WINDOW TITLE BAR */}
      <div className="titlebar">
        <div className="dots"><span className="r"></span><span className="y"></span><span className="g"></span></div>
        <div className="name"><b>ledger</b> — monthly expense tracker</div>
        <div className="month-select" style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <select value={selectedMonth} onChange={(e) => setSelectedMonth(e.target.value)}>
            {allMonths.slice().reverse().map(m => (
              <option key={m} value={m}>{monthLabel(m)}</option>
            ))}
          </select>
          <button className="settings-btn" onClick={openSettings} title="Edit Budgets">⚙️</button>
        </div>
      </div>

      {/* MAIN CONTAINER FRAME */}
      <div className="frame">
        <div className="prompt-line">
          <span>guest@ledger:~$</span>
          <span>cat {monthLabel(selectedMonth).toLowerCase().replace(" ", "_")}.log</span>
          <span className="caret">▌</span>
        </div>

        {/* BURN STATUS */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">burn status</div>
            <div className="panel-sub">{budgetPercentage.toFixed(0)}% of budget used</div>
          </div>
          <div className="burn-top">
            <div className="burn-figure">
              <div className="label">spent this month</div>
              <div className="value">
                {fmtINR(totalSpent)} <small>/ {fmtINR(budgetLimit)}</small>
              </div>
            </div>
            <div className="stat-trio">
              <div className="stat">
                <div className="label">budget</div>
                <div className="value">{fmtINR(budgetLimit)}</div>
              </div>
              <div className="stat">
                <div className="label">remaining</div>
                <div className="value" style={{ color: remainingBudget >= 0 ? "var(--good)" : "var(--bad)" }}>
                  {remainingBudget >= 0 ? fmtINR(remainingBudget) : `-${fmtINR(-remainingBudget)}`}
                </div>
              </div>
              <div className="stat">
                <div className="label">projected month-end</div>
                <div className="value" style={{ color: projectedSpend > budgetLimit ? "var(--bad)" : "var(--good)" }}>
                  {fmtINR(projectedSpend)}
                </div>
              </div>
            </div>
          </div>
          <div className="burn-bar-track">
            <div 
              className={`burn-bar-fill ${budgetPercentage > 100 ? 'over' : ''}`}
              style={{ width: `${Math.min(100, budgetPercentage)}%` }}
            ></div>
            <div className="burn-bar-marker" style={{ left: "100%" }}></div>
          </div>
          <div className="burn-ticks">
            <span>0%</span>
            <span>budget cap →</span>
            <span>{fmtINR(budgetLimit)}</span>
          </div>
        </div>

        {/* DONUT + DAILY GRAPH */}
        <div className="grid-2">
          {/* WHERE THE MONEY GOES */}
          <div className="panel">
            <div className="panel-head">
              <div className="panel-title">where the money goes</div>
            </div>
            <div className="donut-row">
              <svg width="150" height="150" viewBox="0 0 150 150" style={{ flexShrink: 0 }}>
                {/* Background Ring */}
                <circle cx="75" cy="75" r="58" fill="none" stroke="var(--panel-2)" strokeWidth="20" />
                {/* Colored Ring Slices */}
                {totalSpent > 0 && sortedCategories.map(cat => {
                  const frac = categoryTotals[cat] / totalSpent;
                  const sliceLen = frac * donutCircumference;
                  const currentOffset = donutOffset;
                  donutOffset += sliceLen;

                  return (
                    <circle
                      key={cat}
                      cx="75"
                      cy="75"
                      r={donutR}
                      fill="none"
                      stroke={CATEGORY_COLORS[cat] || "#9ca3af"}
                      strokeWidth="20"
                      strokeDasharray={`${sliceLen} ${donutCircumference - sliceLen}`}
                      strokeDashoffset={-currentOffset}
                      transform="rotate(-90 75 75)"
                      style={{ filter: `drop-shadow(0 0 3px ${(CATEGORY_COLORS[cat] || "#9ca3af")}55)` }}
                    />
                  );
                })}
                {/* Center Labels */}
                <text x="75" y="72" textAnchor="middle" fill="var(--text)" fontSize="15" fontFamily="var(--mono)" fontWeight="700">
                  {fmtINR(totalSpent)}
                </text>
                <text x="75" y="89" textAnchor="middle" fill="var(--muted-2)" fontSize="8.5" fontFamily="var(--mono)">
                  TOTAL SPENT
                </text>
              </svg>

              <div className="ledger-list">
                {sortedCategories.length === 0 ? (
                  <div className="empty-note">no spending logged this month yet</div>
                ) : (
                  sortedCategories.map(cat => {
                    const pct = totalSpent > 0 ? (categoryTotals[cat] / totalSpent) * 100 : 0;
                    return (
                      <div key={cat} className="ledger-row">
                        <span className="swatch" style={{ background: CATEGORY_COLORS[cat] || "#9ca3af" }}></span>
                        <span className="cat">{CATEGORY_DISPLAY_NAMES[cat] || cat}</span>
                        <span className="pct">{pct.toFixed(0)}%</span>
                        <span className="amt">{fmtINR(categoryTotals[cat])}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* DAILY BURN LINE CHART */}
          <div className="panel">
            <div className="panel-head">
              <div className="panel-title">daily burn</div>
              <div className="panel-sub">cumulative vs even pace</div>
            </div>
            <svg width="100%" height="190" viewBox="0 0 420 190" preserveAspectRatio="none">
              <defs>
                <linearGradient id="burnGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.55" />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              {[0, 1, 2, 3, 4].map(g => {
                const gy = padT + (plotH * g) / 4;
                const gridVal = maxValBurn * (4 - g) / 4;
                return (
                  <g key={g}>
                    <line x1={padL} x2={burnW - padR} y1={gy} y2={gy} className="grid-line" />
                    <text x={padL - 6} y={gy + 3} textAnchor="end" className="axis-label">
                      {fmtINR(gridVal, false)}
                    </text>
                  </g>
                );
              })}

              {/* Pace Line */}
              {budgetLimit > 0 && (
                <path d={paceLinePath} className="pace-line" />
              )}

              {/* Real Burn Line & Area */}
              {lastDayToPlot > 0 && (
                <>
                  <path d={burnAreaPath} className="burn-area" />
                  <path d={burnLinePath} className="burn-line" />
                </>
              )}

              {/* X Axis Labels */}
              {[1, Math.round(daysTotal / 2), daysTotal].map(d => (
                <text 
                  key={d} 
                  x={burnX(d)} 
                  y={burnH - 6} 
                  textAnchor={d === 1 ? "start" : d === daysTotal ? "end" : "middle"} 
                  className="axis-label"
                >
                  day {d}
                </text>
              ))}
            </svg>
          </div>
        </div>

        {/* MONTH OVER MONTH COMPARE */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">month over month</div>
            <div className="panel-sub">last 6 months, expenses</div>
          </div>
          <div className="scroll-container">
            <svg width="100%" height="160" viewBox="0 0 1000 160" preserveAspectRatio="none" style={{ minWidth: "600px" }}>
              {window6Months.map((m, i) => {
                const val = window6Totals[i];
                const bh = (momH - momPadB - momPadT) * (val / maxValMoM);
                const x = i * momSlot + (momSlot - momBarW) / 2;
                const y = momH - momPadB - bh;

                return (
                  <g key={i}>
                    {/* Background Bar */}
                    <rect 
                      x={i * momSlot + (momSlot - momBarW) / 2} 
                      y={momPadT} 
                      width={momBarW} 
                      height={momH - momPadB - momPadT} 
                      className="mom-bar-bg" 
                      rx="4" 
                    />
                    {/* Filled Bar */}
                    {m && (
                      <>
                        <rect 
                          x={x} 
                          y={y} 
                          width={momBarW} 
                          height={Math.max(bh, 2)} 
                          rx="4" 
                          className={`mom-bar ${m === selectedMonth ? 'current' : ''}`} 
                        />
                        <text x={x + momBarW / 2} y={y - 8} textAnchor="middle" className="mom-value">
                          {fmtINR(val, false)}
                        </text>
                      </>
                    )}
                    {/* Label */}
                    <text x={i * momSlot + momSlot / 2} y={momH - 8} textAnchor="middle" className="mom-label">
                      {m ? monthLabel(m) : "—"}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* BUDGET LIMIT BREAKDOWN */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">budgets & alerts</div>
            <div className="panel-sub">caps turn red when crossed</div>
          </div>
          <div className="budget-rows-container">
            {Object.keys(config.budgets || {}).length === 0 ? (
              <div className="empty-note">no budget caps defined. Edit settings to set budget caps.</div>
            ) : (
              Object.keys(config.budgets || {}).map(cat => {
                const cap = config.budgets[cat];
                const spent = categoryTotals[cat] || 0;
                const pct = cap > 0 ? (spent / cap) * 100 : 0;
                const cls = pct > 100 ? "over" : pct > 80 ? "warn" : "";

                return (
                  <div key={cat} className="budget-row">
                    <span className="cat">{CATEGORY_DISPLAY_NAMES[cat] || cat}</span>
                    <span className="budget-track">
                      <span className={`budget-fill ${cls}`} style={{ width: `${Math.min(100, pct)}%` }}></span>
                    </span>
                    <span className="budget-amt">
                      {fmtINR(spent)} / {fmtINR(cap)}
                      {pct > 100 && <span className="over-tag">OVER</span>}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RECENT ACTIVITY TABLE */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">recent activity</div>
          </div>
          <div className="scroll-container">
            <table className="ledger" style={{ minWidth: "450px" }}>
              <thead>
                <tr>
                  <th>date</th>
                  <th>category</th>
                  <th>note</th>
                  <th style={{ textAlign: "right" }}>amount</th>
                </tr>
              </thead>
              <tbody>
                {currentMonthTxns.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="empty-note" style={{ textAlign: "center" }}>
                      no transactions logged this month yet
                    </td>
                  </tr>
                ) : (
                  currentMonthTxns
                    .slice()
                    .sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id)
                    .slice(0, 12)
                    .map(r => {
                      const labelDate = r.date.slice(8, 10) + " " + monthLabel(selectedMonth).split(" ")[0];
                      return (
                        <tr key={r.id}>
                          <td className="date">{labelDate}</td>
                          <td className="cat">{CATEGORY_DISPLAY_NAMES[r.category] || r.category}</td>
                          <td>{r.note || ""}</td>
                          <td className={`amt ${r.type === 'income' ? 'income' : ''}`} style={{ textAlign: "right" }}>
                            {r.type === 'income' ? '+' : '-'}{fmtINR(r.amount)}
                          </td>
                        </tr>
                      );
                    })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* spending insights */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">spending insights</div>
            <div className="panel-sub">auto-generated</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {insights.map((ins, idx) => (
              <div key={idx} className={`insight-line ${ins.tone || ''}`}>
                <span className="gt">&gt;</span>
                <span dangerouslySetInnerHTML={{ __html: ins.text }} />
              </div>
            ))}
          </div>
        </div>

        <footer className="note">
          100% persistent · connected to Neon cloud database
        </footer>
      </div>

      {/* SETTINGS MODAL */}
      <div className={`modal-overlay ${isModalOpen ? 'open' : ''}`} onClick={(e) => e.target.classList.contains('modal-overlay') && setIsModalOpen(false)}>
        <div className="modal-content">
          <div className="modal-header">
            <div className="modal-title">⚙️ EDIT BUDGETS</div>
            <button className="modal-close" onClick={() => setIsModalOpen(false)}>&times;</button>
          </div>
          <div className="modal-body">
            <div className="form-group">
              <label htmlFor="monthlyBudgetInput">Overall Monthly Budget</label>
              <input 
                type="number" 
                id="monthlyBudgetInput" 
                min="0" 
                step="100"
                value={formMonthlyBudget}
                onChange={(e) => setFormMonthlyBudget(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="budget-title" style={{ marginTop: "18px", fontSize: "12.5px", color: "var(--accent)", fontWeight: 600 }}>
              Category Budget Caps
            </div>
            <div className="budget-grid">
              {config.categories && config.categories.map(cat => (
                <div key={cat} className="form-group">
                  <label>{CATEGORY_DISPLAY_NAMES[cat] || cat.toUpperCase()}</label>
                  <input 
                    type="number" 
                    min="0" 
                    step="100"
                    value={formBudgets[cat] || 0}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      setFormBudgets(prev => ({ ...prev, [cat]: val }));
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={saveSettings}>Save Changes</button>
          </div>
        </div>
      </div>
    </div>
  );
}
