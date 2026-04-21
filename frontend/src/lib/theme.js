const KEY = 'fil_crm_theme';

export function getTheme() {
    if (typeof localStorage === 'undefined') return 'dark';
    const t = localStorage.getItem(KEY);
    return t === 'light' || t === 'dark' ? t : 'dark';
}

export function setTheme(theme) {
    if (theme !== 'dark' && theme !== 'light') return;
    localStorage.setItem(KEY, theme);
    document.documentElement.setAttribute('data-theme', theme);
}

export function toggleTheme() {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
}
