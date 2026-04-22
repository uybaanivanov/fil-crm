const STORAGE_KEY = 'fil_currency';
const RATES_KEY = 'fil_rates';

export function getCurrency() {
    if (typeof localStorage === 'undefined') return 'RUB';
    return localStorage.getItem(STORAGE_KEY) || 'RUB';
}

export function setCurrency(code) {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, code);
    location.reload();
}

export function getRates() {
    if (typeof localStorage === 'undefined') return { usd: null, vnd: null };
    try {
        const raw = localStorage.getItem(RATES_KEY);
        if (!raw) return { usd: null, vnd: null };
        return JSON.parse(raw);
    } catch {
        return { usd: null, vnd: null };
    }
}

export async function refreshRatesIfStale(api) {
    if (typeof localStorage === 'undefined') return;
    const today = new Date().toISOString().slice(0, 10);
    // sessionStorage-флаг защищает от повторного запроса в одной сессии
    // (если localStorage заблокирован Safari private — refresh бил бы каждый mount)
    try {
        if (sessionStorage.getItem('fil_rates_tried') === today) return;
        sessionStorage.setItem('fil_rates_tried', today);
    } catch {
        // sessionStorage тоже может бросать — тогда refresh уйдёт один раз за mount, не критично
    }
    const cached = (() => {
        try { return JSON.parse(localStorage.getItem(RATES_KEY) || '{}'); }
        catch { return {}; }
    })();
    if (cached.updated_at === today) return;
    try {
        const r = await api.get('/currency/rates');
        localStorage.setItem(RATES_KEY, JSON.stringify({
            usd: r.usd, vnd: r.vnd, updated_at: r.updated_at,
        }));
    } catch {
        // молча fallback в RUB
    }
}

const SYM = { RUB: '₽', USD: '$', VND: '₫' };

export function formatMoney(amountRub) {
    if (amountRub == null) return '—';
    const code = getCurrency();
    const rates = getRates();
    if (code === 'USD' && rates.usd) {
        return '$' + (amountRub * rates.usd).toFixed(2);
    }
    if (code === 'VND' && rates.vnd) {
        return '₫' + Math.round(amountRub * rates.vnd).toLocaleString('ru-RU').replace(/,/g, ' ');
    }
    const sign = amountRub < 0 ? '−' : '';
    const abs = Math.round(Math.abs(amountRub)).toLocaleString('ru-RU').replace(/,/g, ' ');
    return sign + abs + ' ₽';
}

export function formatMoneyShort(amountRub) {
    if (amountRub == null) return '—';
    const code = getCurrency();
    const rates = getRates();
    if (code === 'USD' && rates.usd) {
        const v = amountRub * rates.usd;
        if (Math.abs(v) >= 1000) return '$' + (v / 1000).toFixed(1).replace('.0', '') + 'k';
        return '$' + v.toFixed(0);
    }
    if (code === 'VND' && rates.vnd) {
        const v = amountRub * rates.vnd;
        if (Math.abs(v) >= 1_000_000) return '₫' + (v / 1_000_000).toFixed(1).replace('.0', '') + 'M';
        if (Math.abs(v) >= 1000) return '₫' + Math.round(v / 1000) + 'k';
        return '₫' + Math.round(v);
    }
    const abs = Math.abs(amountRub);
    const sign = amountRub < 0 ? '−' : '';
    if (abs >= 1_000_000) return sign + (abs / 1_000_000).toFixed(1).replace('.0', '') + 'М ₽';
    if (abs >= 1000) return sign + Math.round(abs / 1000) + 'к ₽';
    return sign + Math.round(abs) + ' ₽';
}

export const CURRENCIES = ['RUB', 'USD', 'VND'];
export const SYMBOLS = SYM;
