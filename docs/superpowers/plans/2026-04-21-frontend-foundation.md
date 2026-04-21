# Frontend foundation + core screens — Implementation Plan (2/3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести SvelteKit-фронт fil-crm на мобильную warm-earth тему из handoff-дизайна: переписать `app.css`/`app.html` под токены, добавить UI-примитивы в `src/lib/ui/`, переписать `+layout.svelte` с нижним таб-баром, реализовать 6 базовых экранов (`/login`, `/dev_auth`, `/`, `/apartments`, `/bookings`, `/cleaning`) чтобы пользователь мог залогиниться и листать ключевые списки.

**Architecture:** CSS-токены двух тем (`:root` light / `[data-theme="dark"]`) на уровне `app.css` с полной палитрой из `colors_and_type.css` + `THEMES` из `mobile/frame.jsx`. Тема выбирается на старте inline-скриптом в `app.html` перед hydration. Примитивы — Svelte 5 с runes, stateless, принимают `tone`/`size`/контент через slots. `+layout.svelte` фиксирует viewport 390px на мобилке и центрует на десктопе, рендерит нижний 5-иконочный TabBar. Экраны — одна страница = одна `.svelte`, дергают бэк через `lib/api.js`.

**Tech Stack:** SvelteKit 2 + Svelte 5 (runes) · vanilla CSS · google fonts (Instrument Serif, Inter Tight, JetBrains Mono). Бэк — FastAPI endpoints из плана 1/3.

**Спека:** `docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md` разделы 4, 5, 6, 7.
**Исходник примитивов:** `/tmp/design-fetch/extracted/fil-crm/project/mobile/{frame.jsx,ui.jsx,screens-a.jsx,screens-b.jsx}` и `colors_and_type.css`.

Тестирование: ручная верификация в браузере (visual check) через `npm run dev` + взаимодействие. Автоматические тесты на фронте в прототипе не делаем. Backend-тесты уже 41/41 зелёные.

---

## Файловая структура

### Создать
- `frontend/src/lib/theme.js` — get/set theme в localStorage
- `frontend/src/lib/format.js` — `fmtRub`, `fmtShortRub`, `fmtDate`, `fmtNights`, `fmtMonth`
- `frontend/src/lib/ui/Eyebrow.svelte`
- `frontend/src/lib/ui/Chip.svelte`
- `frontend/src/lib/ui/Card.svelte`
- `frontend/src/lib/ui/Section.svelte`
- `frontend/src/lib/ui/Divider.svelte`
- `frontend/src/lib/ui/Chevron.svelte`
- `frontend/src/lib/ui/IconBtn.svelte`
- `frontend/src/lib/ui/AddBtn.svelte`
- `frontend/src/lib/ui/Avatar.svelte`
- `frontend/src/lib/ui/Searchbar.svelte`
- `frontend/src/lib/ui/FilterChips.svelte`
- `frontend/src/lib/ui/PageHead.svelte`
- `frontend/src/lib/ui/ListRow.svelte`
- `frontend/src/lib/ui/TabBar.svelte`
- `frontend/src/routes/dev_auth/+page.svelte` (новый)

### Изменить (переписать целиком)
- `frontend/src/app.css`
- `frontend/src/app.html`
- `frontend/src/lib/api.js`
- `frontend/src/routes/+layout.svelte`
- `frontend/src/routes/+page.svelte` (Сводка) — сейчас placeholder
- `frontend/src/routes/login/+page.svelte`
- `frontend/src/routes/apartments/+page.svelte`
- `frontend/src/routes/bookings/+page.svelte`
- `frontend/src/routes/cleaning/+page.svelte`

### Удалить
- `frontend/src/routes/+layout.js` (тонкий, пустой, если мешает — удаляем в пользу layout.svelte)

Проверить и если пустой/бессмысленный — удалить в задаче рефакторинга layout.

---

## Phase 1 — Foundation

### Task 1: Переписать `app.css` с токенами тем

**Files:**
- Modify (replace): `frontend/src/app.css`

- [ ] **Step 1: Заменить содержимое `frontend/src/app.css`**

```css
/* fil-crm · tokens + base styles. Dark theme by default via data-theme. */

:root {
  /* Light (fallback) */
  --bg: #FBF8F3;
  --bg-subtle: #F5F0E6;
  --card: #FFFFFF;
  --card-hi: #FBF8F3;
  --border: #E8DFCC;
  --border-soft: #EFE7D6;
  --ink: #201812;
  --ink2: #3A2E24;
  --muted: #6B5B4A;
  --faint: #9B8B78;
  --accent: #C06A3A;
  --accent2: #A4542A;
  --accent-bg: #FBEEE5;
  --positive: #5A7A3E;
  --positive-bg: #E8EFE4;
  --caution: #B8882A;
  --caution-bg: #FAEFD6;
  --danger: #B94A2E;
  --danger-bg: #F6DCD4;
  --info: #4A5A6B;
  --info-bg: #E5E8EC;
  --chrome: #F0EADA;
  --chrome-ink: #6B5B4A;

  --font-sans: "Inter Tight", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --font-serif: "Instrument Serif", Georgia, serif;

  --radius-1: 2px;
  --radius-2: 4px;
  --radius-3: 6px;
  --radius-4: 8px;
  --radius-pill: 999px;

  --focus-ring: color-mix(in oklch, var(--accent) 45%, transparent);
}

[data-theme="dark"] {
  --bg: #17120E;
  --bg-subtle: #201813;
  --card: #221A14;
  --card-hi: #2B2118;
  --border: #2F241B;
  --border-soft: #271E16;
  --ink: #F5EEDE;
  --ink2: #D6CBB6;
  --muted: #9A8B74;
  --faint: #6E5F4E;
  --accent: #E08A5A;
  --accent2: #C06A3A;
  --accent-bg: #3A2418;
  --positive: #A8C088;
  --positive-bg: #2A3320;
  --caution: #E4B456;
  --caution-bg: #362A12;
  --danger: #E27A5E;
  --danger-bg: #3B1E17;
  --info: #A6B8CC;
  --info-bg: #1F2830;
  --chrome: #0F0B08;
  --chrome-ink: #B8A992;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-feature-settings: "ss01", "cv11";
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

button {
  font: inherit;
  background: var(--card);
  color: var(--ink);
  border: 1px solid var(--border);
  border-radius: var(--radius-3);
  padding: 10px 14px;
  cursor: pointer;
}
button:hover { background: var(--card-hi); }
button.primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
button.primary:hover { background: var(--accent2); border-color: var(--accent2); }
button.ghost { background: transparent; border-color: transparent; }

input, select, textarea {
  font: inherit;
  background: var(--card);
  color: var(--ink);
  border: 1px solid var(--border);
  border-radius: var(--radius-3);
  padding: 10px 12px;
  width: 100%;
}
input::placeholder, textarea::placeholder { color: var(--faint); }

.num, .mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum", "zero";
}

.eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--faint);
  font-weight: 500;
}

.error-banner {
  background: var(--danger-bg);
  color: var(--danger);
  border: 1px solid var(--danger);
  padding: 10px 12px;
  border-radius: var(--radius-3);
  margin: 12px 16px;
}

/* Mobile-first: фиксим viewport 390px для мобильного, центруем на десктопе */
.app-shell {
  max-width: 390px;
  min-height: 100vh;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  position: relative;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 72px; /* место под TabBar */
}

:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
  border-radius: var(--radius-1);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app.css
git commit -m "feat(frontend): CSS-токены двух тем + базовые стили"
```

---

### Task 2: Переписать `app.html` — шрифты + theme bootstrap

**Files:**
- Modify (replace): `frontend/src/app.html`

- [ ] **Step 1: Заменить содержимое `frontend/src/app.html`**

```html
<!doctype html>
<html lang="ru" data-theme="dark">
	<head>
		<meta charset="utf-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
		<meta name="color-scheme" content="light dark" />
		<meta name="theme-color" content="#17120E" />
		<link rel="preconnect" href="https://fonts.googleapis.com" />
		<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
		<link
			href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
			rel="stylesheet"
		/>
		<script>
			// Apply stored theme BEFORE render to avoid flash.
			(function () {
				try {
					var t = localStorage.getItem("fil_crm_theme") || "dark";
					if (t !== "dark" && t !== "light") t = "dark";
					document.documentElement.setAttribute("data-theme", t);
				} catch (e) {}
			})();
		</script>
		%sveltekit.head%
	</head>
	<body data-sveltekit-preload-data="hover">
		<div style="display: contents">%sveltekit.body%</div>
	</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app.html
git commit -m "feat(frontend): шрифты + theme bootstrap в app.html"
```

---

### Task 3: `src/lib/theme.js`

**Files:**
- Create: `frontend/src/lib/theme.js`

- [ ] **Step 1: Создать файл**

```js
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/theme.js
git commit -m "feat(frontend): lib/theme.js — get/set/toggle theme"
```

---

### Task 4: `src/lib/format.js`

**Files:**
- Create: `frontend/src/lib/format.js`

- [ ] **Step 1: Создать файл**

```js
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/format.js
git commit -m "feat(frontend): lib/format.js — rub / date / nights / role"
```

---

### Task 5: Расширить `src/lib/api.js`

**Files:**
- Modify: `frontend/src/lib/api.js`

- [ ] **Step 1: Переписать файл**

```js
import { getUser } from './auth.js';

const BASE = 'http://localhost:8000';

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `HTTP ${status}`);
        this.status = status;
        this.detail = detail;
    }
}

async function request(method, path, body, { auth = true } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
        const user = getUser();
        if (user) headers['X-User-Id'] = String(user.id);
    }
    const res = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body)
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, data.detail || `HTTP ${res.status}`);
    return data;
}

export const api = {
    get:    (path, opts)       => request('GET',    path, undefined, opts),
    post:   (path, body, opts) => request('POST',   path, body,      opts),
    patch:  (path, body, opts) => request('PATCH',  path, body,      opts),
    delete: (path, opts)       => request('DELETE', path, undefined, opts)
};

// Helper: определить, жив ли dev-picker. Не бросает — возвращает bool.
export async function isDevPickerAvailable() {
    try {
        const res = await fetch(`${BASE}/dev_auth/users`);
        return res.ok;
    } catch {
        return false;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.js
git commit -m "feat(frontend): api.js — isDevPickerAvailable helper"
```

---

## Phase 2 — UI primitives

### Task 6: Примитивы (часть 1) — Eyebrow, Chip, Card, Section, Divider, Chevron

**Files:**
- Create: `frontend/src/lib/ui/Eyebrow.svelte`
- Create: `frontend/src/lib/ui/Chip.svelte`
- Create: `frontend/src/lib/ui/Card.svelte`
- Create: `frontend/src/lib/ui/Section.svelte`
- Create: `frontend/src/lib/ui/Divider.svelte`
- Create: `frontend/src/lib/ui/Chevron.svelte`

- [ ] **Step 1: Eyebrow.svelte**

```svelte
<script>
    let { children } = $props();
</script>

<div class="eyebrow">{@render children?.()}</div>

<style>
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        font-weight: 500;
    }
</style>
```

- [ ] **Step 2: Chip.svelte**

```svelte
<script>
    let { tone = 'info', children } = $props();
    const MAP = {
        ok:     ['var(--positive-bg)', 'var(--positive)'],
        due:    ['var(--caution-bg)',  'var(--caution)'],
        late:   ['var(--danger-bg)',   'var(--danger)'],
        info:   ['var(--info-bg)',     'var(--info)'],
        draft:  ['var(--bg-subtle)',   'var(--muted)'],
        accent: ['var(--accent-bg)',   'var(--accent)']
    };
    const [bg, fg] = $derived(MAP[tone] || MAP.info);
</script>

<span class="chip" style:background={bg} style:color={fg}>
    <span class="dot" style:background={fg}></span>
    {@render children?.()}
</span>

<style>
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 3px;
        white-space: nowrap;
    }
    .dot {
        width: 4px;
        height: 4px;
        border-radius: 999px;
    }
</style>
```

- [ ] **Step 3: Card.svelte**

```svelte
<script>
    let { pad = 16, style = '', children } = $props();
</script>

<div class="card" style:padding="{pad}px" style={style}>
    {@render children?.()}
</div>

<style>
    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
</style>
```

- [ ] **Step 4: Section.svelte**

```svelte
<script>
    let { title, action = null, children, style = '' } = $props();
</script>

<div class="section" style={style}>
    <div class="head">
        <span class="eyebrow">{title}</span>
        {#if action}<span class="action">{action}</span>{/if}
    </div>
    {@render children?.()}
</div>

<style>
    .section { margin-bottom: 14px; }
    .head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        padding: 0 20px 8px;
    }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        font-weight: 500;
    }
    .action {
        font-size: 12px;
        color: var(--accent);
        font-weight: 500;
    }
</style>
```

- [ ] **Step 5: Divider.svelte**

```svelte
<div class="divider"></div>

<style>
    .divider {
        height: 1px;
        background: var(--border-soft);
    }
</style>
```

- [ ] **Step 6: Chevron.svelte**

```svelte
<svg width="6" height="12" viewBox="0 0 6 12" fill="none" aria-hidden="true">
    <path d="M1 1l4 5-4 5" stroke="var(--faint)" stroke-width="1.5" stroke-linecap="round" />
</svg>
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/ui/Eyebrow.svelte frontend/src/lib/ui/Chip.svelte frontend/src/lib/ui/Card.svelte frontend/src/lib/ui/Section.svelte frontend/src/lib/ui/Divider.svelte frontend/src/lib/ui/Chevron.svelte
git commit -m "feat(ui): примитивы — Eyebrow, Chip, Card, Section, Divider, Chevron"
```

---

### Task 7: Примитивы (часть 2) — IconBtn, AddBtn, Avatar, Searchbar, FilterChips, ListRow

**Files:**
- Create: `frontend/src/lib/ui/IconBtn.svelte`
- Create: `frontend/src/lib/ui/AddBtn.svelte`
- Create: `frontend/src/lib/ui/Avatar.svelte`
- Create: `frontend/src/lib/ui/Searchbar.svelte`
- Create: `frontend/src/lib/ui/FilterChips.svelte`
- Create: `frontend/src/lib/ui/ListRow.svelte`

- [ ] **Step 1: IconBtn.svelte**

```svelte
<script>
    let {
        d,
        bg = 'transparent',
        color = 'var(--ink2)',
        size = 36,
        border = true,
        onclick = null,
        title = ''
    } = $props();
</script>

<button
    class="icon-btn"
    style:width="{size}px"
    style:height="{size}px"
    style:border-radius="{size/2}px"
    style:background={bg}
    style:border={(border && bg === 'transparent') ? '1px solid var(--border)' : 'none'}
    title={title}
    onclick={onclick}
    type="button"
>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <path d={d} />
    </svg>
</button>

<style>
    .icon-btn {
        padding: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        cursor: pointer;
    }
    .icon-btn:hover { opacity: 0.85; }
</style>
```

- [ ] **Step 2: AddBtn.svelte**

```svelte
<script>
    let { onclick = null, title = 'Добавить' } = $props();
</script>

<button class="add-btn" onclick={onclick} title={title} type="button" aria-label={title}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round">
        <path d="M12 5v14M5 12h14" />
    </svg>
</button>

<style>
    .add-btn {
        width: 40px;
        height: 40px;
        border-radius: 20px;
        background: var(--accent);
        border: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        padding: 0;
    }
    .add-btn:hover { background: var(--accent2); }
</style>
```

- [ ] **Step 3: Avatar.svelte**

```svelte
<script>
    let { name = '', size = 36, accent = null } = $props();
    const initials = $derived(
        (name || '?').split(' ').map(s => s[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()
    );
</script>

<div
    class="avatar"
    style:width="{size}px"
    style:height="{size}px"
    style:border-radius="{size/2}px"
    style:font-size="{Math.round(size*0.33)}px"
    style:background={accent || 'var(--bg-subtle)'}
    style:color={accent ? '#fff' : 'var(--ink)'}
>
    {initials}
</div>

<style>
    .avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-weight: 600;
        flex-shrink: 0;
    }
</style>
```

- [ ] **Step 4: Searchbar.svelte**

```svelte
<script>
    let { placeholder = 'Поиск…', value = $bindable(''), oninput = null } = $props();
</script>

<label class="searchbar">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--faint)" stroke-width="1.8">
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
    </svg>
    <input
        type="search"
        {placeholder}
        bind:value
        oninput={oninput}
    />
</label>

<style>
    .searchbar {
        height: 40px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
    }
    input {
        flex: 1;
        border: none;
        padding: 0;
        background: transparent;
        color: var(--ink);
        width: 100%;
    }
    input:focus-visible { outline: none; }
    input::placeholder { color: var(--faint); }
</style>
```

- [ ] **Step 5: FilterChips.svelte**

```svelte
<script>
    // items: [{ label, count?, value, active? }]
    let { items = [], onselect = null } = $props();
</script>

<div class="chips">
    {#each items as item}
        <button
            class="chip"
            class:active={item.active}
            type="button"
            onclick={() => onselect?.(item.value)}
        >
            {item.label}
            {#if item.count != null}<span class="count">{item.count}</span>{/if}
        </button>
    {/each}
</div>

<style>
    .chips {
        display: flex;
        gap: 8px;
        padding: 0 20px 14px;
        overflow-x: auto;
    }
    .chip {
        padding: 6px 12px;
        border-radius: 999px;
        background: var(--card);
        color: var(--ink);
        border: 1px solid var(--border);
        font-size: 12px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
        cursor: pointer;
    }
    .chip.active {
        background: var(--ink);
        color: var(--bg);
        border-color: var(--ink);
    }
    .count {
        font-family: var(--font-mono);
        font-size: 10px;
        opacity: 0.6;
    }
</style>
```

- [ ] **Step 6: ListRow.svelte**

```svelte
<script>
    let {
        title = '',
        sub = null,
        left = null,
        right = null,
        onclick = null,
        last = false
    } = $props();
</script>

<button class="row" class:last onclick={onclick} type="button">
    {#if left}<div class="left">{@render left()}</div>{/if}
    <div class="body">
        <div class="title">{title}</div>
        {#if sub}<div class="sub">{@render sub()}</div>{/if}
    </div>
    {#if right}<div class="right">{@render right()}</div>{/if}
</button>

<style>
    .row {
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
        background: transparent;
        border-top: none;
        border-left: none;
        border-right: none;
        width: 100%;
        text-align: left;
        cursor: pointer;
    }
    .row.last { border-bottom: none; }
    .row:hover { background: var(--card-hi); }
    .body { flex: 1; min-width: 0; }
    .title {
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        letter-spacing: -0.1px;
    }
    .sub {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
</style>
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/ui/IconBtn.svelte frontend/src/lib/ui/AddBtn.svelte frontend/src/lib/ui/Avatar.svelte frontend/src/lib/ui/Searchbar.svelte frontend/src/lib/ui/FilterChips.svelte frontend/src/lib/ui/ListRow.svelte
git commit -m "feat(ui): примитивы — IconBtn, AddBtn, Avatar, Searchbar, FilterChips, ListRow"
```

---

### Task 8: Примитивы (часть 3) — PageHead, TabBar

**Files:**
- Create: `frontend/src/lib/ui/PageHead.svelte`
- Create: `frontend/src/lib/ui/TabBar.svelte`

- [ ] **Step 1: PageHead.svelte**

```svelte
<script>
    // title: string | snippet; sub, right, back, backOnClick — опциональные
    let { title, sub = null, right = null, back = null, backOnClick = null } = $props();
</script>

<div class="head">
    {#if back}
        <div class="back-row">
            <button class="back" onclick={backOnClick} type="button">
                <svg width="8" height="14" viewBox="0 0 8 14" aria-hidden="true">
                    <path d="M7 1L1 7l6 6" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" />
                </svg>
                <span>{back}</span>
            </button>
            {#if right}<div class="right">{@render right()}</div>{/if}
        </div>
    {/if}
    <div class="title-row" class:with-back={!!back}>
        <div class="title-wrap">
            <h1 class="title">{@render (typeof title === 'function' ? title : () => title)()}</h1>
            {#if sub}<div class="sub">{sub}</div>{/if}
        </div>
        {#if !back && right}<div class="right">{@render right()}</div>{/if}
    </div>
</div>

<style>
    .back-row {
        padding: 10px 16px 4px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .back {
        background: transparent;
        border: none;
        padding: 0;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--accent);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
    }
    .title-row {
        padding: 14px 20px 18px;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 12px;
    }
    .title-row.with-back { padding-top: 6px; }
    .title {
        font-family: var(--font-serif);
        font-size: 32px;
        line-height: 1;
        letter-spacing: -0.5px;
        color: var(--ink);
        font-weight: 400;
        margin: 0;
    }
    .sub {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--faint);
        margin-top: 8px;
    }
    .right { flex-shrink: 0; }
</style>
```

Примечание по использованию `title`: можно передать строку (`title="Квартиры"`) или сниппет (`<PageHead>{#snippet title()}...{/snippet}</PageHead>`). Текущая реализация оборачивает строку в функцию.

Упрощённая версия (строка-only) — если Svelte 5 runes капризничают с `{@render (typeof title === 'function' ? ...)}`, замени блок на:

```svelte
<h1 class="title">{title}</h1>
```

И принимай только строку. Остальные 6 экранов этого плана передают заголовок именно строкой.

- [ ] **Step 2: TabBar.svelte**

```svelte
<script>
    import { page } from '$app/state';
    import { goto } from '$app/navigation';

    const TABS = [
        { id: 'home',       label: 'Сводка',    href: '/',           d: 'M3 10.5 10 4l7 6.5V16a1 1 0 0 1-1 1h-3v-5H8v5H5a1 1 0 0 1-1-1z' },
        { id: 'apartments', label: 'Квартиры',  href: '/apartments', d: 'M4 17V7l6-3 6 3v10M8 11h4M8 14h4M8 8h4' },
        { id: 'bookings',   label: 'Брони',     href: '/bookings',   d: 'M6 3v3M14 3v3M3 8h14M4 5h12a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z' },
        { id: 'cleaning',   label: 'Уборка',    href: '/cleaning',   d: 'M16 5 9 13l-4-4' },
        { id: 'profile',    label: 'Профиль',   href: '/settings',   d: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z' }
    ];

    function isActive(href) {
        const path = page.url.pathname;
        if (href === '/') return path === '/';
        return path === href || path.startsWith(href + '/');
    }
</script>

<nav class="tabbar">
    {#each TABS as tab}
        <button
            class="tab"
            class:active={isActive(tab.href)}
            onclick={() => goto(tab.href)}
            type="button"
        >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"
                 stroke={isActive(tab.href) ? 'var(--accent)' : 'var(--faint)'}
                 stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d={tab.d} />
            </svg>
            <span>{tab.label}</span>
        </button>
    {/each}
</nav>

<style>
    .tabbar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        max-width: 390px;
        margin: 0 auto;
        background: var(--card);
        border-top: 1px solid var(--border);
        display: flex;
        padding: 6px 0 4px;
        z-index: 10;
    }
    .tab {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        padding: 3px 0;
        background: transparent;
        border: none;
        cursor: pointer;
        color: var(--faint);
    }
    .tab.active { color: var(--accent); font-weight: 600; }
    .tab span {
        font-size: 10px;
        font-weight: 500;
    }
    .tab.active span { font-weight: 600; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/ui/PageHead.svelte frontend/src/lib/ui/TabBar.svelte
git commit -m "feat(ui): PageHead + TabBar"
```

---

## Phase 3 — Layout

### Task 9: Переписать `+layout.svelte`

**Files:**
- Modify (replace): `frontend/src/routes/+layout.svelte`

- [ ] **Step 1: Проверить, что `+layout.js` не мешает**

Run: `cat frontend/src/routes/+layout.js`
Если содержит только экспорт без побочных эффектов — можно оставить.
Если он ставил какие-то ssr/prerender флаги, сохранить их.

- [ ] **Step 2: Заменить содержимое `frontend/src/routes/+layout.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import TabBar from '$lib/ui/TabBar.svelte';
    import { getUser } from '$lib/auth.js';
    import '../app.css';

    let { children } = $props();
    let ready = $state(false);
    let user = $state(null);

    // Пути, где TabBar скрыт (auth-flow) и guard'ы не действуют
    const PUBLIC = ['/login', '/dev_auth'];

    function isPublic(path) {
        return PUBLIC.some(p => path === p || path.startsWith(p + '/'));
    }

    onMount(() => {
        user = getUser();
        const path = page.url.pathname;
        if (!user && !isPublic(path)) {
            goto('/login');
            return;
        }
        if (user && path === '/login') {
            goto(user.role === 'maid' ? '/cleaning' : '/');
            return;
        }
        ready = true;
    });

    let showTabs = $derived(user && !isPublic(page.url.pathname));
</script>

{#if ready}
    <div class="app-shell">
        <main class="app-main">
            {@render children?.()}
        </main>
        {#if showTabs}<TabBar />{/if}
    </div>
{/if}
```

- [ ] **Step 3: Dev-server smoke**

В отдельном терминале:
```bash
cd frontend && npm run dev -- --port 5173
```

Открыть `http://localhost:5173` в браузере — должно редиректить на `/login` (пользователь не залогинен). Экран будет пустой (login ещё не переписан) — это нормально, мы этим займёмся в Task 10. Главное — нет ошибок в консоли, CSS переменные применены (фон тёмный), шрифты подгружены.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/+layout.svelte
git commit -m "feat(frontend): layout — 390px shell + TabBar + auth-guard"
```

---

## Phase 4 — Core screens

### Task 10: `/login` — декоративный

**Files:**
- Modify (replace): `frontend/src/routes/login/+page.svelte`

- [ ] **Step 1: Заменить содержимое**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { isDevPickerAvailable } from '$lib/api.js';

    let devAvailable = $state(false);
    let email = $state('aisen@fil-crm.ru');
    let password = $state('');
    let showPass = $state(false);

    onMount(async () => {
        devAvailable = await isDevPickerAvailable();
    });

    function submit(e) {
        e.preventDefault();
        // Декоративный экран — ничего не делаем.
        // В проде здесь был бы POST /auth/login.
    }
</script>

<div class="page">
    <div class="brand">
        <div class="logo">f</div>
        <span class="word">fil<span class="dash">-</span>crm</span>
    </div>

    <h1 class="greeting">С возвращением<span class="dot-accent">.</span></h1>
    <p class="sub">Войдите, чтобы управлять квартирами, бронями и уборкой.</p>

    <form onsubmit={submit}>
        <label class="field-label">Телефон или e-mail</label>
        <input type="email" bind:value={email} class="field" />

        <label class="field-label">Пароль</label>
        <div class="pass-wrap">
            <input
                type={showPass ? 'text' : 'password'}
                bind:value={password}
                class="field pass-input"
                placeholder="••••••••"
            />
            <button type="button" class="show" onclick={() => (showPass = !showPass)}>
                {showPass ? 'Скрыть' : 'Показать'}
            </button>
        </div>

        <a href="#" class="forgot">Забыли пароль?</a>

        <button type="submit" class="primary-btn">Войти →</button>
    </form>

    {#if devAvailable}
        <button class="dev-link" onclick={() => goto('/dev_auth')} type="button">
            → Dev picker (без пароля)
        </button>
    {/if}

    <div class="version">v2.1.0 · Якутск</div>
</div>

<style>
    .page {
        min-height: 100vh;
        padding: 40px 28px 20px;
        display: flex;
        flex-direction: column;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 44px;
    }
    .logo {
        width: 22px;
        height: 22px;
        background: var(--ink);
        color: var(--bg);
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 700;
    }
    .word { font-family: var(--font-mono); font-size: 15px; font-weight: 500; }
    .dash { color: var(--accent); }
    .greeting {
        font-family: var(--font-serif);
        font-size: 38px;
        line-height: 1;
        letter-spacing: -0.6px;
        color: var(--ink);
        margin: 0 0 10px;
        font-weight: 400;
    }
    .dot-accent { color: var(--accent); }
    .sub {
        font-size: 14px;
        color: var(--muted);
        margin: 0 0 36px;
    }
    .field-label {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        font-weight: 500;
        display: block;
        margin-bottom: 8px;
    }
    .field {
        height: 48px;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 14px;
        background: var(--card);
        color: var(--ink);
        font-size: 15px;
        margin-bottom: 14px;
    }
    .pass-wrap {
        position: relative;
        margin-bottom: 12px;
    }
    .pass-input {
        border: 1.5px solid var(--accent);
        padding-right: 70px;
        margin-bottom: 0;
    }
    .show {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        color: var(--accent);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
    }
    .forgot {
        display: block;
        font-size: 13px;
        color: var(--accent);
        font-weight: 500;
        margin-bottom: 24px;
    }
    .primary-btn {
        height: 50px;
        background: var(--accent);
        border: none;
        border-radius: 6px;
        color: #fff;
        font-size: 15px;
        font-weight: 600;
        width: 100%;
        cursor: pointer;
    }
    .dev-link {
        margin-top: 16px;
        background: transparent;
        border: 1px dashed var(--border);
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 12px;
        padding: 10px;
        cursor: pointer;
        border-radius: 6px;
    }
    .version {
        margin-top: auto;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding-top: 24px;
    }
</style>
```

- [ ] **Step 2: Verify**

В dev-сервере — открыть `/login`:
- Нет ошибок в консоли
- Шрифты загружены (Instrument Serif для заголовка)
- Dev-picker ссылка показывается, только если бэк запущен с `DEBUG=1`
- Submit формы ничего не делает

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/login/+page.svelte
git commit -m "feat(frontend): /login — декоративный экран + dev-picker linkback"
```

---

### Task 11: `/dev_auth` — picker

**Files:**
- Create: `frontend/src/routes/dev_auth/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { setUser } from '$lib/auth.js';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRole } from '$lib/format.js';

    let users = $state([]);
    let loading = $state(true);
    let error = $state(null);

    onMount(async () => {
        try {
            users = await api.get('/dev_auth/users', { auth: false });
        } catch (e) {
            if (e instanceof ApiError && e.status === 404) {
                error = 'Dev-picker отключён. Запусти backend с DEBUG=1.';
            } else {
                error = e.message || 'Ошибка загрузки';
            }
        } finally {
            loading = false;
        }
    });

    async function pick(u) {
        try {
            const profile = await api.post('/dev_auth/login', { user_id: u.id }, { auth: false });
            setUser(profile);
            goto(profile.role === 'maid' ? '/cleaning' : '/');
        } catch (e) {
            error = e.message || 'Не удалось войти';
        }
    }
</script>

<div class="page">
    <header class="head">
        <button class="back" onclick={() => goto('/login')} type="button">← Назад</button>
        <h1 class="title">Dev picker</h1>
        <div class="sub">Вход без пароля — только локально</div>
    </header>

    {#if loading}
        <div class="state">Загрузка…</div>
    {:else if error}
        <div class="state error">{error}</div>
    {:else if users.length === 0}
        <div class="state">В базе нет пользователей. Создай через sqlite или POST /users.</div>
    {:else}
        <ul class="list">
            {#each users as u}
                <li>
                    <button onclick={() => pick(u)} class="user" type="button">
                        <Avatar name={u.full_name} size={40} accent="var(--ink)" />
                        <div class="body">
                            <div class="name">{u.full_name}</div>
                            <div class="role">{fmtRole(u.role)}</div>
                        </div>
                        <div class="id">#{u.id}</div>
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .page { padding: 28px 20px 40px; }
    .head { margin-bottom: 20px; }
    .back {
        background: transparent;
        border: none;
        color: var(--accent);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        padding: 0 0 12px;
    }
    .title {
        font-family: var(--font-serif);
        font-size: 28px;
        margin: 0;
        font-weight: 400;
        color: var(--ink);
    }
    .sub {
        font-family: var(--font-mono);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--faint);
        margin-top: 4px;
    }
    .state { padding: 20px 0; color: var(--muted); }
    .state.error { color: var(--danger); }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .user {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        cursor: pointer;
        text-align: left;
    }
    .user:hover { background: var(--card-hi); }
    .body { flex: 1; }
    .name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .role {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        margin-top: 2px;
    }
    .id {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--faint);
    }
</style>
```

- [ ] **Step 2: Verify**

Запусти бэк с `DEBUG=1` (из .env):
```bash
uv run --env-file .env uvicorn backend.main:app --port 8000
```

В sqlite добавь пользователя (если ещё нет):
```bash
uv run --env-file .env python -c "from backend.db import get_conn; \
  with get_conn() as c: c.execute(\"INSERT INTO users(full_name, role) VALUES ('Айсен Петров', 'owner')\"); c.commit(); print('OK')"
```

В браузере `/dev_auth` — должен показать карточку юзера. Клик → редирект на `/`. После `/` видим TabBar внизу.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/dev_auth/+page.svelte
git commit -m "feat(frontend): /dev_auth — dev-picker"
```

---

### Task 12: `/` — Сводка

**Files:**
- Modify (replace): `frontend/src/routes/+page.svelte`

- [ ] **Step 1: Заменить содержимое**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtShortRub, fmtRub, fmtMonth } from '$lib/format.js';

    let user = $state(null);
    let data = $state(null);
    let error = $state(null);

    onMount(async () => {
        user = getUser();
        try {
            data = await api.get('/dashboard/summary');
        } catch (e) {
            error = e.message;
        }
    });

    const maxDaily = $derived(data ? Math.max(1, ...data.daily_series) : 1);
    const todayIdx = $derived(data ? (new Date().getDate() - 1) : 0);
</script>

<PageHead title="Доброе утро" sub={user?.full_name?.split(' ')[0] ?? ''} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if !data}
    <div class="loading">Загрузка…</div>
{:else}
    <div class="kpis">
        <Card pad={14}>
            <div class="eyebrow">Занято</div>
            <div class="num big">
                {data.occupancy.occupied}<span class="slash">/{data.occupancy.total}</span>
            </div>
        </Card>
        <Card pad={14}>
            <div class="eyebrow">Выручка · {fmtMonth(data.month)}</div>
            <div class="num big">{fmtShortRub(data.revenue_mtd)}</div>
            {#if data.revenue_prev_month > 0}
                {@const delta = Math.round(((data.revenue_mtd - data.revenue_prev_month) / data.revenue_prev_month) * 100)}
                <div class="delta" class:pos={delta >= 0} class:neg={delta < 0}>
                    {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)}% к {fmtMonth(data.month).split(' ')[0]}
                </div>
            {/if}
        </Card>
    </div>

    <Section title="Выручка — {fmtMonth(data.month)}">
        <div class="chart-wrap">
            <Card pad={14}>
                <svg viewBox="0 0 300 70" width="100%" height="70" preserveAspectRatio="none">
                    {#each data.daily_series as v, i}
                        {@const h = (v / maxDaily) * 64}
                        {@const isToday = i === todayIdx}
                        {@const isFuture = i > todayIdx}
                        <rect
                            x={i * (300 / data.daily_series.length) + 1}
                            y={70 - h}
                            width={Math.max(1, 300 / data.daily_series.length - 2)}
                            height={Math.max(0, h)}
                            fill={isToday ? 'var(--accent)' : isFuture ? 'var(--border-soft)' : 'var(--ink2)'}
                        />
                    {/each}
                </svg>
                <div class="chart-axis">
                    <span>1</span>
                    <span>10</span>
                    <span class="today">{todayIdx + 1} · СЕГ</span>
                    <span>{data.daily_series.length}</span>
                </div>
            </Card>
        </div>
    </Section>

    <Section title="Сегодня">
        <div class="events">
            {#if data.today_events.length === 0}
                <Card pad={16}>
                    <div class="empty">Событий нет</div>
                </Card>
            {:else}
                {#each data.today_events as ev}
                    <div class="event">
                        <div class="time">{ev.time}</div>
                        <div class="event-body">
                            <div class="kind {ev.kind}">{ev.kind === 'check_in' ? 'Заезд' : 'Выезд'} · {ev.client_name}</div>
                            <div class="addr">{ev.apartment_address}</div>
                        </div>
                        <div class="event-right">
                            {#if ev.total_price != null}
                                <div class="amt">{fmtRub(ev.total_price)}</div>
                            {/if}
                            <Chip tone={ev.kind === 'check_in' ? 'ok' : 'draft'}>
                                {ev.kind === 'check_in' ? 'заезд' : 'выезд'}
                            </Chip>
                        </div>
                    </div>
                {/each}
            {/if}
        </div>
    </Section>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--muted); text-align: center; }
    .kpis {
        padding: 8px 20px 16px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .big {
        font-family: var(--font-serif);
        font-size: 32px;
        line-height: 1;
        margin-top: 8px;
        color: var(--ink);
    }
    .slash { font-size: 16px; color: var(--faint); font-family: var(--font-mono); }
    .delta {
        font-family: var(--font-mono);
        font-size: 10px;
        margin-top: 6px;
    }
    .delta.pos { color: var(--positive); }
    .delta.neg { color: var(--danger); }
    .chart-wrap { padding: 0 20px 16px; }
    .chart-axis {
        display: flex;
        justify-content: space-between;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 6px;
    }
    .chart-axis .today { color: var(--accent); }
    .events { padding: 0 20px; display: flex; flex-direction: column; gap: 8px; }
    .event {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 11px 14px;
        display: grid;
        grid-template-columns: 48px 1fr auto;
        gap: 10px;
        align-items: center;
    }
    .time {
        font-family: var(--font-mono);
        font-size: 12px;
        font-weight: 600;
        color: var(--ink);
    }
    .kind { font-size: 13px; font-weight: 600; color: var(--ink); }
    .addr {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
        text-transform: uppercase;
    }
    .event-right { text-align: right; display: flex; flex-direction: column; gap: 4px; align-items: flex-end; }
    .amt {
        font-family: var(--font-mono);
        font-size: 12px;
        font-weight: 600;
        color: var(--ink);
    }
    .empty { color: var(--faint); text-align: center; padding: 12px; }
</style>
```

- [ ] **Step 2: Verify**

С залогиненным owner'ом (через `/dev_auth`), зайти на `/`. Должна загрузиться сводка. Без данных показываются пустые KPI и empty-state «Событий нет».

Если в бэке есть квартиры и брони — KPI заполняются, график рисуется, сегодняшние события видны.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/+page.svelte
git commit -m "feat(frontend): / — сводка (KPI + график + сегодня)"
```

---

### Task 13: `/apartments` — список

**Files:**
- Modify (replace): `frontend/src/routes/apartments/+page.svelte`

- [ ] **Step 1: Заменить содержимое**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api } from '$lib/api.js';
    import { goto } from '$app/navigation';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Searchbar from '$lib/ui/Searchbar.svelte';
    import FilterChips from '$lib/ui/FilterChips.svelte';
    import AddBtn from '$lib/ui/AddBtn.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import { fmtMonth } from '$lib/format.js';

    let apartments = $state([]);
    let error = $state(null);
    let loading = $state(true);
    let query = $state('');
    let filter = $state('all');

    const currentMonth = new Date().toISOString().slice(0, 7);

    onMount(async () => {
        try {
            apartments = await api.get(`/apartments?with_stats=1&month=${currentMonth}`);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    const counts = $derived({
        all: apartments.length,
        occupied: apartments.filter(a => a.status === 'occupied').length,
        free: apartments.filter(a => a.status === 'free').length,
        needs_cleaning: apartments.filter(a => a.status === 'needs_cleaning').length
    });

    const filterItems = $derived([
        { label: 'Все',       value: 'all',            count: counts.all,            active: filter === 'all' },
        { label: 'Занято',    value: 'occupied',       count: counts.occupied,       active: filter === 'occupied' },
        { label: 'Свободно',  value: 'free',           count: counts.free,           active: filter === 'free' },
        { label: 'Уборка',    value: 'needs_cleaning', count: counts.needs_cleaning, active: filter === 'needs_cleaning' }
    ]);

    const visible = $derived(
        apartments
            .filter(a => filter === 'all' || a.status === filter)
            .filter(a => {
                if (!query) return true;
                const q = query.toLowerCase();
                return (a.title || '').toLowerCase().includes(q)
                    || (a.address || '').toLowerCase().includes(q);
            })
    );

    function statusChip(a) {
        if (a.status === 'occupied') return { tone: 'ok', label: 'Занята' };
        if (a.status === 'needs_cleaning') return { tone: 'due', label: 'Уборка' };
        return { tone: 'draft', label: 'Свободна' };
    }

    function metaLine(a) {
        const parts = [];
        if (a.rooms) parts.push(a.rooms);
        if (a.area_m2) parts.push(`${a.area_m2} м²`);
        if (a.district) parts.push(a.district);
        return parts.join(' · ') || '—';
    }
</script>

<PageHead
    title="Квартиры"
    sub="{apartments.length} объектов · {counts.occupied} занято"
>
    {#snippet right()}
        <AddBtn onclick={() => goto('/apartments/new')} />
    {/snippet}
</PageHead>

<div class="search-row">
    <div class="search"><Searchbar bind:value={query} placeholder="Адрес, название…" /></div>
</div>

<FilterChips items={filterItems} onselect={(v) => (filter = v)} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else if visible.length === 0}
    <div class="empty">Ничего не найдено</div>
{:else}
    <div class="list">
        {#each visible as a}
            <button class="apt" onclick={() => goto(`/apartments/${a.id}`)} type="button">
                {#if a.cover_url}
                    <img src={a.cover_url} alt="" class="cover" />
                {:else}
                    <div class="cover placeholder">{(a.title || a.address || '?').slice(0, 2).toUpperCase()}</div>
                {/if}
                <div class="apt-body">
                    <div class="apt-head">
                        <div class="title">{a.title}</div>
                        {#each [statusChip(a)] as s}
                            <Chip tone={s.tone}>{s.label}</Chip>
                        {/each}
                    </div>
                    <div class="addr">{a.address}</div>
                    <div class="meta">{metaLine(a)}</div>
                    <div class="util-row">
                        <div class="bar">
                            <div class="bar-fill" style:width="{Math.round((a.utilization || 0) * 100)}%"></div>
                        </div>
                        <span class="util-num">{Math.round((a.utilization || 0) * 100)}%</span>
                    </div>
                </div>
            </button>
        {/each}
    </div>
{/if}

<style>
    .search-row { padding: 0 20px 14px; }
    .loading, .empty { padding: 40px 20px; color: var(--faint); text-align: center; }
    .list { padding: 0 20px 20px; display: flex; flex-direction: column; gap: 10px; }
    .apt {
        display: flex;
        gap: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: left;
        cursor: pointer;
        width: 100%;
    }
    .apt:hover { background: var(--card-hi); }
    .cover {
        width: 64px;
        height: 64px;
        border-radius: 6px;
        object-fit: cover;
        flex-shrink: 0;
        background: var(--bg-subtle);
    }
    .cover.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 14px;
        color: var(--faint);
        font-weight: 600;
    }
    .apt-body { flex: 1; min-width: 0; }
    .apt-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 4px;
    }
    .title {
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .addr {
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 4px;
    }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 10px;
    }
    .util-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .bar {
        flex: 1;
        height: 3px;
        background: var(--border-soft);
        border-radius: 2px;
        overflow: hidden;
    }
    .bar-fill { height: 100%; background: var(--accent); }
    .util-num {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--muted);
        min-width: 32px;
        text-align: right;
    }
</style>
```

**Note:** Этот экран использует `PageHead` со snippet'ом `right`. Если реализация `PageHead` из Task 8 не поддерживает snippet — замени на простую string-title + `right` как prop-сниппет. Ниже образец строгой замены — если не работает, упрости `PageHead` до принимающего `title` string и `right` как snippet через `{#snippet right}...{/snippet}` внутри вызова.

- [ ] **Step 2: Verify**

С залогиненным owner'ом. Если в БД есть квартиры — видим список с cover (если задан) или плейсхолдером, чипом статуса, полоской загрузки.
Если список пуст — empty-state. Поиск и фильтр-чипы работают на фронте.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/apartments/+page.svelte
git commit -m "feat(frontend): /apartments — список с фильтром и загрузкой"
```

---

### Task 14: `/bookings` — список с группировкой по дням

**Files:**
- Modify (replace): `frontend/src/routes/bookings/+page.svelte`

- [ ] **Step 1: Заменить содержимое**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api } from '$lib/api.js';
    import { goto } from '$app/navigation';
    import PageHead from '$lib/ui/PageHead.svelte';
    import AddBtn from '$lib/ui/AddBtn.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import { fmtRub, fmtDateFull, fmtNights } from '$lib/format.js';

    let bookings = $state([]);
    let clients = $state([]);
    let error = $state(null);
    let loading = $state(true);
    let tab = $state('all'); // all | check_in | check_out | cancelled

    onMount(async () => {
        try {
            const [b, c] = await Promise.all([
                api.get('/bookings'),
                api.get('/clients')
            ]);
            bookings = b;
            clients = c;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    const clientById = $derived(Object.fromEntries(clients.map(c => [c.id, c])));

    // Для таб-фильтра нам нужен список событий (каждая бронь = 2 события: check_in + check_out)
    // Для табов «Все» / «Заезды» / «Выезды» / «Отменённые» мы группируем «события» по дате.
    // tab=all — показываем только «check_in события» (как основной поток),
    // но «cancelled» бронь показываем только в tab=cancelled.

    const events = $derived.by(() => {
        const out = [];
        for (const b of bookings) {
            if (b.status === 'cancelled' && tab !== 'cancelled') continue;
            if (tab === 'cancelled' && b.status !== 'cancelled') continue;
            if (tab === 'check_in')   out.push({ ...b, kind: 'check_in', date: b.check_in });
            else if (tab === 'check_out') out.push({ ...b, kind: 'check_out', date: b.check_out });
            else if (tab === 'cancelled') out.push({ ...b, kind: 'cancelled', date: b.check_in });
            else { // all — показываем и заезды, и выезды
                out.push({ ...b, kind: 'check_in', date: b.check_in });
                out.push({ ...b, kind: 'check_out', date: b.check_out });
            }
        }
        out.sort((a, b) => a.date.localeCompare(b.date));
        return out;
    });

    const groups = $derived.by(() => {
        const g = new Map();
        for (const e of events) {
            if (!g.has(e.date)) g.set(e.date, []);
            g.get(e.date).push(e);
        }
        return Array.from(g.entries()).map(([date, items]) => ({ date, items }));
    });

    function toneFor(ev) {
        if (ev.status === 'cancelled') return 'late';
        if (ev.status === 'completed') return 'ok';
        return 'accent';
    }

    function statusLabel(status) {
        return { active: 'активная', completed: 'закрыта', cancelled: 'отменена' }[status] || status;
    }

    function sourceOf(ev) {
        const c = clientById[ev.client_id];
        return c?.source || '—';
    }

    const tabs = $derived([
        { value: 'all',        label: 'Все',        active: tab === 'all' },
        { value: 'check_in',   label: 'Заезды',     active: tab === 'check_in' },
        { value: 'check_out',  label: 'Выезды',     active: tab === 'check_out' },
        { value: 'cancelled',  label: 'Отменённые', active: tab === 'cancelled' }
    ]);
</script>

<PageHead title="Брони" sub="{bookings.filter(b => b.status === 'active').length} активных">
    {#snippet right()}
        <AddBtn onclick={() => goto('/bookings/new')} />
    {/snippet}
</PageHead>

<div class="tabs">
    {#each tabs as t}
        <button class="tab" class:active={t.active} type="button" onclick={() => (tab = t.value)}>
            {t.label}
        </button>
    {/each}
</div>

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else if groups.length === 0}
    <div class="empty">Нет броней</div>
{:else}
    {#each groups as group}
        <div class="group">
            <div class="day-head">
                <span class="eyebrow">{fmtDateFull(group.date)}</span>
                <span class="count">{group.items.length} бр.</span>
            </div>
            <div class="items">
                {#each group.items as ev}
                    <button class="ev" onclick={() => goto(`/bookings/${ev.id}`)} type="button">
                        <div
                            class="stripe"
                            style:background={ev.kind === 'check_in' ? 'var(--positive)' : 'var(--muted)'}
                        ></div>
                        <div class="ev-body">
                            <div class="ev-head">
                                <span class="time">{ev.kind === 'check_in' ? '14:00' : '12:00'}</span>
                                <span class="kind {ev.kind}">
                                    {ev.kind === 'check_in' ? 'ЗАЕЗД' : 'ВЫЕЗД'}
                                </span>
                            </div>
                            <div class="name">{ev.client_name}</div>
                            <div class="meta">
                                {ev.apartment_title} · {sourceOf(ev)}
                            </div>
                        </div>
                        <div class="ev-right">
                            <div class="amt">{fmtRub(ev.total_price)}</div>
                            <div class="nights">{fmtNights(ev.check_in, ev.check_out)}</div>
                            <Chip tone={toneFor(ev)}>{statusLabel(ev.status)}</Chip>
                        </div>
                    </button>
                {/each}
            </div>
        </div>
    {/each}
{/if}

<style>
    .tabs {
        padding: 0 20px 16px;
        display: flex;
        gap: 6px;
    }
    .tab {
        flex: 1;
        height: 34px;
        border-radius: 6px;
        background: var(--card);
        color: var(--ink2);
        border: 1px solid var(--border);
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
    }
    .tab.active {
        background: var(--accent);
        color: #fff;
        border-color: var(--accent);
    }
    .loading, .empty { padding: 40px 20px; color: var(--faint); text-align: center; }
    .group { margin-bottom: 14px; padding: 0 20px; }
    .day-head {
        display: flex;
        justify-content: space-between;
        padding-bottom: 8px;
    }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--faint);
        font-weight: 500;
    }
    .count {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
    }
    .items { display: flex; flex-direction: column; gap: 8px; }
    .ev {
        display: grid;
        grid-template-columns: 4px 1fr auto;
        gap: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 11px 14px;
        cursor: pointer;
        text-align: left;
    }
    .ev:hover { background: var(--card-hi); }
    .stripe { border-radius: 2px; }
    .ev-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 3px;
    }
    .time {
        font-family: var(--font-mono);
        font-size: 12px;
        font-weight: 600;
        color: var(--ink);
        opacity: 0.7;
    }
    .kind {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .kind.check_in { color: var(--positive); }
    .kind.check_out { color: var(--muted); }
    .name { font-size: 13px; font-weight: 600; color: var(--ink); }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 3px;
        text-transform: uppercase;
    }
    .ev-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .amt {
        font-family: var(--font-mono);
        font-size: 12px;
        font-weight: 600;
        color: var(--ink);
    }
    .nights {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
</style>
```

- [ ] **Step 2: Verify**

С залогиненным owner'ом. Список броней сгруппирован по дням. Табы переключают фильтрацию. Источник подтягивается из `client.source`. Статус-чипы цветные.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/bookings/+page.svelte
git commit -m "feat(frontend): /bookings — группы по дням, таб-фильтры, источник"
```

---

### Task 15: `/cleaning` — список требующих уборки

**Files:**
- Modify (replace): `frontend/src/routes/cleaning/+page.svelte`

- [ ] **Step 1: Заменить содержимое**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api } from '$lib/api.js';
    import { goto } from '$app/navigation';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import { fmtRub } from '$lib/format.js';

    let apartments = $state([]);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        try {
            apartments = await api.get('/apartments/cleaning');
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function markClean(apt, e) {
        e.stopPropagation();
        try {
            await api.post(`/apartments/${apt.id}/mark-clean`);
            apartments = apartments.filter(a => a.id !== apt.id);
        } catch (err) {
            error = err.message;
        }
    }

    onMount(load);
</script>

<PageHead title="Уборка" sub="{apartments.length} в очереди" />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else if apartments.length === 0}
    <div class="empty">
        <Card pad={20}>
            <div class="empty-text">Все квартиры чистые ✓</div>
        </Card>
    </div>
{:else}
    <div class="list">
        {#each apartments as a}
            <button class="task" onclick={() => goto(`/apartments/${a.id}`)} type="button">
                <div class="top">
                    <div class="addr-wrap">
                        <div class="title">{a.title}</div>
                        <div class="addr">{a.address}</div>
                    </div>
                    <Chip tone="due">Требует уборки</Chip>
                </div>
                <div class="meta">
                    {a.rooms || '—'}
                    {#if a.area_m2} · {a.area_m2} м²{/if}
                    {#if a.district} · {a.district}{/if}
                    · {fmtRub(a.price_per_night)}/ноч
                </div>
                <div class="actions">
                    <button class="primary" onclick={(e) => markClean(a, e)} type="button">
                        Закрыть уборку ✓
                    </button>
                </div>
            </button>
        {/each}
    </div>
{/if}

<style>
    .loading, .empty { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty-text { text-align: center; color: var(--positive); font-weight: 600; }
    .list { padding: 0 20px 20px; display: flex; flex-direction: column; gap: 10px; }
    .task {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px;
        cursor: pointer;
        text-align: left;
        width: 100%;
    }
    .task:hover { background: var(--card-hi); }
    .top {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        align-items: flex-start;
        margin-bottom: 8px;
    }
    .addr-wrap { flex: 1; min-width: 0; }
    .title {
        font-size: 15px;
        font-weight: 600;
        color: var(--ink);
    }
    .addr {
        font-size: 12px;
        color: var(--muted);
        margin-top: 2px;
    }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 12px;
    }
    .actions { display: flex; justify-content: flex-end; }
    .primary {
        padding: 10px 14px;
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary:hover { background: var(--accent2); }
</style>
```

- [ ] **Step 2: Verify**

Создай тестовую квартиру с `needs_cleaning=1`:
```bash
uv run --env-file .env python -c "from backend.db import get_conn; \
  with get_conn() as c: \
    c.execute(\"INSERT INTO apartments(title, address, price_per_night, needs_cleaning) VALUES ('Лермонтова 58/24', 'ул. Лермонтова, 58, кв. 24', 4280, 1)\"); \
    c.commit(); print('OK')"
```

На `/cleaning` должна появиться карточка. Нажать «Закрыть уборку» — карточка исчезает, в бэке `needs_cleaning=0`.

Роль `maid` имеет доступ к этому эндпоинту (по бэку).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/cleaning/+page.svelte
git commit -m "feat(frontend): /cleaning — список и закрытие уборки"
```

---

## Phase 5 — Финал

### Task 16: Удалить старые routes-файлы, которые больше не нужны

**Files:**
- Delete: `frontend/src/routes/clients/+page.svelte` (будет переписан в плане 3/3)
- Delete: `frontend/src/routes/users/+page.svelte` (будет переписан в плане 3/3)

**Примечание:** эти файлы были в старом интерфейсе и не соответствуют новой теме. Оставлять их с неконсистентным видом плохо. Удаляем — Svelte-роутер отдаст 404 при переходе, и в плане 3/3 мы их перепишем.

- [ ] **Step 1: Удалить файлы**

```bash
rm frontend/src/routes/clients/+page.svelte
rm frontend/src/routes/users/+page.svelte
rmdir frontend/src/routes/clients frontend/src/routes/users 2>/dev/null || true
```

- [ ] **Step 2: Commit**

```bash
git add -A frontend/src/routes/clients frontend/src/routes/users
git commit -m "chore(frontend): удалить старые /clients и /users (перепишем в плане 3/3)"
```

---

### Task 17: Дымовой прогон и обновление спеки

- [ ] **Step 1: Запустить дев-сервер + бэк, проверить каждый экран вручную**

Бэк (в первом терминале):
```bash
uv run --env-file .env uvicorn backend.main:app --port 8000
```

Фронт (во втором):
```bash
cd frontend && npm run dev -- --port 5173
```

Открыть `http://localhost:5173` в мобильном viewport (DevTools → Toggle device toolbar → 390px):

1. `/login` — декоративный экран, шрифты загружены, dev-picker линк виден (бэк запущен с DEBUG=1).
2. `/dev_auth` — список юзеров, клик → логин → редирект.
3. `/` — Сводка: KPI, график, сегодняшние события.
4. `/apartments` — список, фильтры, поиск, утилизация.
5. `/bookings` — группы по дням, табы, источник.
6. `/cleaning` — список требующих уборки, кнопка закрытия работает.
7. TabBar внизу фиксирован, активная вкладка подсвечивается.
8. Тёмная тема по умолчанию.

Если где-то ошибка — зафиксировать и откатиться к соответствующему таску.

- [ ] **Step 2: Обновить спеку**

Отредактировать `docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md` — отметить второй план как готовый:

```markdown
- [x] Backend (план 1/3) — готов 2026-04-21
- [x] Frontend foundation + core screens (план 2/3) — готов 2026-04-21
- [ ] Frontend remaining screens (план 3/3)
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md
git commit -m "docs(spec): отметка о завершении frontend foundation"
```

---

## Готово

После выполнения этого плана:

- Фронт полностью переверстан на мобильную warm-earth тему с двумя темами.
- UI-примитивы готовы к использованию в следующих экранах.
- TabBar-навигация работает, auth-guard на месте.
- 6 базовых экранов живые, данные идут из бэка.
- Пользователь может: залогиниться через `/dev_auth`, увидеть сводку, полистать квартиры с утилизацией, полистать брони с группировкой по дням, закрыть уборку.

Следующий шаг — **план 3/3**: остальные экраны (`/apartments/:id`, `/apartments/new`, `/bookings/:id`, `/bookings/new`, `/calendar`, `/clients`, `/clients/:id`, `/finance`, `/reports`, `/users`, `/settings`).
