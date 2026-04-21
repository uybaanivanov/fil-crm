// Форматирование чисел, дат, валюты.

const MONTHS_SHORT = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];

export function fmtRub(n) {
    if (n === null || n === undefined) return '—';
    const s = Math.round(Math.abs(n)).toLocaleString('ru-RU').replace(/,/g, ' ');
    return (n < 0 ? '−' : '') + s + ' ₽';
}

export function fmtShortRub(n) {
    if (n === null || n === undefined) return '—';
    const abs = Math.abs(n);
    const sign = n < 0 ? '−' : '';
    if (abs >= 1_000_000) return sign + (abs / 1_000_000).toFixed(1).replace('.0', '') + 'М ₽';
    if (abs >= 1_000)     return sign + Math.round(abs / 1_000) + 'к ₽';
    return sign + abs + ' ₽';
}

export function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso + 'T00:00:00');
    return String(d.getDate()).padStart(2, '0') + '.' + String(d.getMonth() + 1).padStart(2, '0');
}

export function fmtDateFull(iso) {
    if (!iso) return '';
    const d = new Date(iso + 'T00:00:00');
    return d.getDate() + ' ' + MONTHS_SHORT[d.getMonth()] + ' ' + d.getFullYear();
}

export function fmtMonth(ym) {
    // '2026-04' → 'апрель 2026'
    if (!ym) return '';
    const [y, m] = ym.split('-').map(Number);
    const names = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь'];
    return names[m - 1] + ' ' + y;
}

export function fmtNights(ci, co) {
    if (!ci || !co) return '';
    const a = new Date(ci + 'T00:00:00');
    const b = new Date(co + 'T00:00:00');
    const n = Math.max(0, Math.round((b - a) / 86400000));
    return n + ' ноч' + (n % 10 === 1 && n % 100 !== 11 ? 'ь' : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? 'и' : 'ей'));
}

export function fmtRole(role) {
    return { owner: 'Владелец', admin: 'Администратор', maid: 'Горничная' }[role] || role;
}
