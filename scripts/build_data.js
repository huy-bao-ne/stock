const fs = require('fs');
const path = require('path');

const SECTORS = {
  BANKING: "Ngân hàng",
  REALESTATE: "Bất động sản",
  TECHNOLOGY: "Công nghệ",
  FOOD: "Thực phẩm & Đồ uống",
  CONSTRUCTION: "Xây dựng",
  TRANSPORT: "Vận tải - Kho bãi",
  CHEMICALS: "SX Nhựa - Hóa chất",
  UTILITIES: "Tiện ích",
  SECURITIES: "Chứng khoán",
  HEALTHCARE: "Chăm sóc sức khỏe"
};

const ROOT = path.resolve(__dirname, '..');
const FACTOR_DIR = path.join(ROOT, 'factor');
const OUTPUT_DATA_DIR = path.join(ROOT, 'web', 'src', 'data');

// Tạo thư mục đích nếu chưa có
if (!fs.existsSync(OUTPUT_DATA_DIR)) {
  fs.mkdirSync(OUTPUT_DATA_DIR, { recursive: true });
}

function parseCSV(content) {
  // Bỏ BOM nếu có
  if (content.charCodeAt(0) === 0xFEFF) {
    content = content.slice(1);
  }
  const lines = content.split(/\r?\n/).filter(line => line.trim().length > 0);
  if (lines.length === 0) return [];

  // Parse header
  const headers = parseCSVLine(lines[0]);
  const rows = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    if (values.length === 0 || (values.length === 1 && values[0] === '')) continue;
    const row = {};
    headers.forEach((h, idx) => {
      let val = values[idx] !== undefined ? values[idx].trim() : '';
      row[h] = val;
    });
    rows.push(row);
  }
  return rows;
}

function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

// 1. Process Factor Results per Sector
const sectorsFactors = {};
const sectorsSummary = [];
const allTickersSet = new Set();
const tickersDetail = {};

for (const [key, label] of Object.entries(SECTORS)) {
  const sKey = key.toLowerCase();
  const factorPath = path.join(FACTOR_DIR, 'outputs', sKey, `${sKey}_factor_results.csv`);
  let factors = [];

  if (fs.existsSync(factorPath)) {
    const raw = fs.readFileSync(factorPath, 'utf8');
    const rows = parseCSV(raw);
    factors = rows.map(r => {
      const corrStr = r['độ_tương_quan_%'] || '0%';
      const corrVal = parseFloat(corrStr.replace('%', '').trim()) || 0;
      const pVal = parseFloat(r['p_value']) || 0;
      const obs = parseInt(r['số_quan_sát']) || 0;
      const sigRaw = String(r['có_ý_nghĩa_thống_kê'] || '').trim().toLowerCase();
      const bonfRaw = String(r['có_ý_nghĩa_sau_bonferroni'] || '').trim().toLowerCase();

      return {
        rank: parseInt(r['xếp_hạng']) || 0,
        factor: r['chỉ_báo'] || '',
        category: r['loại_chỉ_báo'] || 'Chỉ số',
        correlation_percent: corrStr,
        correlation_value: corrVal,
        direction: r['kết_luận'] || (corrVal > 0 ? 'Đồng biến' : 'Nghịch biến'),
        strength: r['độ_mạnh'] || 'Yếu',
        p_value: pVal,
        is_significant: sigRaw === 'true',
        is_bonferroni_sig: bonfRaw === 'true',
        bonferroni_threshold: parseFloat(r['bonferroni_threshold']) || 0.0025,
        observations: obs
      };
    });
  }

  sectorsFactors[key] = {
    key,
    label,
    factors
  };

  const sigCount = factors.filter(f => f.is_significant).length;
  const bonfCount = factors.filter(f => f.is_bonferroni_sig).length;
  const maxObs = factors.length > 0 ? Math.max(...factors.map(f => f.observations)) : 0;
  const topFactor = factors.length > 0 ? factors[0] : null;

  sectorsSummary.push({
    key,
    label,
    factors_tested: factors.length,
    observations_max: maxObs,
    significant_p05: sigCount,
    significant_bonferroni: bonfCount,
    top_factor: topFactor ? topFactor.factor : '—',
    top_correlation: topFactor ? topFactor.correlation_percent : '—',
    top_correlation_value: topFactor ? topFactor.correlation_value : 0
  });

  // Load Gold Factors for Tickers
  const goldPath = path.join(FACTOR_DIR, 'data', sKey, 'gold_factors.csv');
  if (fs.existsSync(goldPath)) {
    const rawGold = fs.readFileSync(goldPath, 'utf8');
    const goldRows = parseCSV(rawGold);

    goldRows.forEach(row => {
      const ticker = (row['mã_chứng_khoán'] || '').trim().toUpperCase();
      const year = parseInt(row['năm']);
      if (!ticker || isNaN(year)) return;

      allTickersSet.add(ticker);

      if (!tickersDetail[ticker]) {
        tickersDetail[ticker] = {
          ticker,
          sector_key: key,
          sector_label: label,
          yearly_data: []
        };
      }

      // Parse numerical values
      const parsedRow = { year };
      for (const [k, v] of Object.entries(row)) {
        if (k === 'mã_chứng_khoán' || k === 'năm') continue;
        const numVal = parseFloat(v);
        parsedRow[k] = isNaN(numVal) ? v : numVal;
      }
      tickersDetail[ticker].yearly_data.push(parsedRow);
    });
  }
}

// Sort ticker yearly data by year ascending
for (const ticker of Object.keys(tickersDetail)) {
  tickersDetail[ticker].yearly_data.sort((a, b) => a.year - b.year);
}

// List of all tickers with summary stats
const tickersList = Object.values(tickersDetail).map(t => {
  const lastYear = t.yearly_data.length > 0 ? t.yearly_data[t.yearly_data.length - 1] : null;
  const prevYear = t.yearly_data.length > 1 ? t.yearly_data[t.yearly_data.length - 2] : null;

  const roa = lastYear ? lastYear['roa_%'] : null;
  const roe = lastYear ? lastYear['roe_%'] : null;
  const ret = lastYear ? lastYear['lợi_nhuận_hàng_năm_%'] : null;

  let roaDelta = null;
  if (lastYear && prevYear && lastYear['roa_%'] != null && prevYear['roa_%'] != null) {
    roaDelta = parseFloat((lastYear['roa_%'] - prevYear['roa_%']).toFixed(2));
  }
  let roeDelta = null;
  if (lastYear && prevYear && lastYear['roe_%'] != null && prevYear['roe_%'] != null) {
    roeDelta = parseFloat((lastYear['roe_%'] - prevYear['roe_%']).toFixed(2));
  }

  return {
    ticker: t.ticker,
    sector_key: t.sector_key,
    sector_label: t.sector_label,
    years_count: t.yearly_data.length,
    latest_year: lastYear ? lastYear.year : null,
    latest_roa: roa != null && typeof roa === 'number' ? parseFloat(roa.toFixed(2)) : null,
    latest_roe: roe != null && typeof roe === 'number' ? parseFloat(roe.toFixed(2)) : null,
    latest_return: ret != null && typeof ret === 'number' ? parseFloat(ret.toFixed(2)) : null,
    roa_delta: roaDelta,
    roe_delta: roeDelta
  };
}).sort((a, b) => a.ticker.localeCompare(b.ticker));

// Write JSON files
fs.writeFileSync(path.join(OUTPUT_DATA_DIR, 'sectors_summary.json'), JSON.stringify(sectorsSummary, null, 2), 'utf8');
fs.writeFileSync(path.join(OUTPUT_DATA_DIR, 'sectors_factors.json'), JSON.stringify(sectorsFactors, null, 2), 'utf8');
fs.writeFileSync(path.join(OUTPUT_DATA_DIR, 'tickers_detail.json'), JSON.stringify(tickersDetail, null, 2), 'utf8');
fs.writeFileSync(path.join(OUTPUT_DATA_DIR, 'tickers_list.json'), JSON.stringify(tickersList, null, 2), 'utf8');

console.log('✅ Chuyển đổi dữ liệu thành công!');
console.log(`- 10 ngành: ${sectorsSummary.length}`);
console.log(`- Tổng số mã cổ phiếu: ${tickersList.length}`);
console.log(`- Lưu vào: ${OUTPUT_DATA_DIR}`);
