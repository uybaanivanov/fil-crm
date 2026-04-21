const KEY = 'fil_crm_user';

export function getUser() {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
}

export function setUser(user) {
    localStorage.setItem(KEY, JSON.stringify(user));
}

export function clearUser() {
    localStorage.removeItem(KEY);
}
