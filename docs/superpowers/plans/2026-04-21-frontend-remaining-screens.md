# Frontend remaining screens — Implementation Plan (3/3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Достроить все оставшиеся экраны мобильного дизайна: детальные страницы (`/apartments/:id`, `/bookings/:id`, `/clients/:id`), формы создания (`/apartments/new`, `/bookings/new`), шахматку `/calendar`, списки и экраны админ/инфраструктуры (`/clients`, `/finance`, `/reports`, `/users`, `/settings`). После этого плана полный спек реализован.

**Architecture:** Каждый экран — один `+page.svelte` под `frontend/src/routes/`. Переиспользуем примитивы из плана 2/3 (`$lib/ui/*`) и формат-утилиты (`$lib/format.js`). Для модальных диалогов (создание расхода) — inline-блок раскрывающийся через `$state`, без отдельной модалки. Для переключателя тем в `/settings` используем `$lib/theme.js`.

**Tech Stack:** SvelteKit 2 + Svelte 5 runes. UI-примитивы из плана 2/3.

**Спека:** `docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md` раздел 4.
**Исходник оригинального дизайна:** `/tmp/design-fetch/extracted/fil-crm/project/mobile/screens-{a,b}.jsx`.

Тестирование: `npm run build` после каждого экрана — должен собираться без ошибок. Ручная проверка в dev-сервере по мере возможности.

---

## Файловая структура

Все новые файлы:

- `frontend/src/routes/apartments/[id]/+page.svelte`
- `frontend/src/routes/apartments/new/+page.svelte`
- `frontend/src/routes/bookings/[id]/+page.svelte`
- `frontend/src/routes/bookings/new/+page.svelte`
- `frontend/src/routes/calendar/+page.svelte`
- `frontend/src/routes/clients/+page.svelte`
- `frontend/src/routes/clients/[id]/+page.svelte`
- `frontend/src/routes/finance/+page.svelte`
- `frontend/src/routes/reports/+page.svelte`
- `frontend/src/routes/users/+page.svelte`
- `frontend/src/routes/settings/+page.svelte`

---

## Phase 1 — Admin & info screens (простые)

### Task 1: `/settings` — Профиль, тема, выход

**Files:**
- Create: `frontend/src/routes/settings/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import Chevron from '$lib/ui/Chevron.svelte';
    import { getUser, clearUser } from '$lib/auth.js';
    import { getTheme, setTheme } from '$lib/theme.js';
    import { fmtRole } from '$lib/format.js';

    let user = $state(null);
    let theme = $state('dark');

    onMount(() => {
        user = getUser();
        theme = getTheme();
    });

    function choose(t) {
        theme = t;
        setTheme(t);
    }

    function logout() {
        clearUser();
        goto('/login');
    }

    // Лаунчер на остальные экраны
    const links = [
        { href: '/clients',  label: 'Клиенты' },
        { href: '/calendar', label: 'Шахматка' },
        { href: '/finance',  label: 'Финансы' },
        { href: '/reports',  label: 'Отчёты' }
    ];
    // /users виден только owner'у
</script>

<PageHead title="Настройки" sub={user ? `${user.full_name} · ${fmtRole(user.role)}` : ''} />

{#if user}
    <div class="wrap">
        <!-- Профиль -->
        <Card pad={14}>
            <div class="profile">
                <Avatar name={user.full_name} size={56} accent="var(--ink)" />
                <div class="profile-body">
                    <div class="name">{user.full_name}</div>
                    <div class="email">#{user.id} · {fmtRole(user.role)}</div>
                </div>
            </div>
        </Card>
    </div>

    <!-- Разделы -->
    <Section title="Разделы">
        <div class="wrap">
            <Card pad={0}>
                {#each links as l, i}
                    <button class="link" onclick={() => goto(l.href)} type="button" class:last={i === links.length - 1 && user.role !== 'owner'}>
                        <span>{l.label}</span>
                        <Chevron />
                    </button>
                {/each}
                {#if user.role === 'owner'}
                    <button class="link last" onclick={() => goto('/users')} type="button">
                        <span>Команда</span>
                        <Chevron />
                    </button>
                {/if}
            </Card>
        </div>
    </Section>

    <!-- Тема -->
    <Section title="Оформление">
        <div class="wrap">
            <Card pad={14}>
                <div class="theme-row">
                    <div>
                        <div class="lbl">Тёмная тема</div>
                        <div class="hint">По умолчанию</div>
                    </div>
                    <div class="switch" class:on={theme === 'dark'} onclick={() => choose(theme === 'dark' ? 'light' : 'dark')} role="switch" aria-checked={theme === 'dark'} tabindex="0" onkeydown={(e) => { if (e.key === ' ' || e.key === 'Enter') choose(theme === 'dark' ? 'light' : 'dark'); }}>
                        <div class="knob"></div>
                    </div>
                </div>
                <div class="seg">
                    {#each [['Тёмная','dark'], ['Светлая','light']] as [lbl, val]}
                        <button class="seg-btn" class:active={theme === val} type="button" onclick={() => choose(val)}>
                            {lbl}
                        </button>
                    {/each}
                </div>
            </Card>
        </div>
    </Section>

    <!-- Выход -->
    <div class="wrap">
        <button class="logout" onclick={logout} type="button">Выйти</button>
    </div>
{/if}

<style>
    .wrap { padding: 0 20px 14px; }
    .profile { display: flex; align-items: center; gap: 14px; }
    .profile-body { flex: 1; }
    .name { font-family: var(--font-serif); font-size: 22px; color: var(--ink); letter-spacing: -0.3px; }
    .email { font-family: var(--font-mono); font-size: 11px; color: var(--faint); margin-top: 4px; }
    .link {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 14px;
        background: transparent;
        border: none;
        border-bottom: 1px solid var(--border-soft);
        font-size: 14px;
        color: var(--ink);
        cursor: pointer;
        text-align: left;
    }
    .link.last { border-bottom: none; }
    .link:hover { background: var(--card-hi); }
    .theme-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .lbl { font-size: 14px; font-weight: 600; color: var(--ink); }
    .hint {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        margin-top: 2px;
    }
    .switch {
        width: 46px;
        height: 26px;
        border-radius: 13px;
        background: var(--border-soft);
        position: relative;
        cursor: pointer;
        transition: background 0.2s;
    }
    .switch.on { background: var(--accent); }
    .knob {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 22px;
        height: 22px;
        border-radius: 11px;
        background: #fff;
        transition: left 0.2s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .switch.on .knob { left: 22px; }
    .seg {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px;
    }
    .seg-btn {
        padding: 8px 0;
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        color: var(--ink2);
        cursor: pointer;
    }
    .seg-btn.active {
        background: var(--card-hi);
        border-color: var(--accent);
        color: var(--accent);
    }
    .logout {
        width: 100%;
        background: transparent;
        color: var(--danger);
        border: 1px solid var(--danger);
        padding: 12px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
    }
    .logout:hover { background: var(--danger-bg); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/settings/+page.svelte
git commit -m "feat(frontend): /settings — профиль, темы, разделы, выход"
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: `✓ built in …` (no errors).

---

### Task 2: `/users` — Команда (owner only)

**Files:**
- Create: `frontend/src/routes/users/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRole } from '$lib/format.js';

    let users = $state([]);
    let me = $state(null);
    let error = $state(null);
    let loading = $state(true);

    onMount(async () => {
        me = getUser();
        if (!me || me.role !== 'owner') {
            error = 'Доступно только владельцу';
            loading = false;
            return;
        }
        try {
            users = await api.get('/users');
        } catch (e) {
            if (e instanceof ApiError && e.status === 403) {
                error = 'Нет прав';
            } else {
                error = e.message;
            }
        } finally {
            loading = false;
        }
    });

    const byRole = $derived({
        owner: users.filter(u => u.role === 'owner'),
        admin: users.filter(u => u.role === 'admin'),
        maid:  users.filter(u => u.role === 'maid')
    });
</script>

<PageHead title="Команда" sub="{users.length} пользователей"
    back="Настройки" backOnClick={() => goto('/settings')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else}
    <Section title="Пользователи">
        <div class="wrap">
            <Card pad={0}>
                {#each users as u, i}
                    <div class="row" class:last={i === users.length - 1}>
                        <Avatar name={u.full_name} size={38} accent={u.role === 'owner' ? 'var(--ink)' : null} />
                        <div class="body">
                            <div class="name">
                                {u.full_name}
                                {#if me && u.id === me.id}<span class="you">ВЫ</span>{/if}
                            </div>
                            <div class="meta">{fmtRole(u.role).toUpperCase()} · #{u.id}</div>
                        </div>
                    </div>
                {/each}
            </Card>
        </div>
    </Section>

    <Section title="Роли">
        <div class="wrap">
            <Card pad={0}>
                {#each [
                    ['Владелец', 'полный доступ', byRole.owner.length],
                    ['Администратор', 'брони, клиенты, квартиры', byRole.admin.length],
                    ['Горничная', 'только уборка', byRole.maid.length]
                ] as [n, d, c], i}
                    <div class="role-row" class:last={i === 2}>
                        <div>
                            <div class="role-name">{n}</div>
                            <div class="role-meta">{d.toUpperCase()} · {c}</div>
                        </div>
                    </div>
                {/each}
            </Card>
        </div>
    </Section>
{/if}

<style>
    .wrap { padding: 0 20px 14px; }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .row {
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
    }
    .row.last { border-bottom: none; }
    .body { flex: 1; min-width: 0; }
    .name {
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .you {
        font-family: var(--font-mono);
        font-size: 9px;
        background: var(--ink);
        color: var(--bg);
        padding: 1px 5px;
        border-radius: 2px;
        letter-spacing: 0.5px;
    }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }
    .role-row {
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-soft);
    }
    .role-row.last { border-bottom: none; }
    .role-name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .role-meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/users/+page.svelte
git commit -m "feat(frontend): /users — команда (owner-only)"
```

- [ ] **Step 3: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 3: `/reports` — Отчёты

**Files:**
- Create: `frontend/src/routes/reports/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import { fmtShortRub, fmtRub } from '$lib/format.js';

    let period = $state('month');
    let data = $state(null);
    let error = $state(null);
    let loading = $state(true);

    async function load(p) {
        loading = true;
        try {
            data = await api.get(`/reports?period=${p}`);
            period = p;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(() => load('month'));

    const periods = [
        ['week', 'Неделя'],
        ['month', 'Месяц'],
        ['quarter', 'Квартал'],
        ['year', 'Год']
    ];
</script>

<PageHead title="Отчёты" sub={period} back="Настройки" backOnClick={() => goto('/settings')} />

<div class="tabs">
    {#each periods as [val, lbl]}
        <button class="tab" class:active={period === val} type="button" onclick={() => load(val)}>
            {lbl}
        </button>
    {/each}
</div>

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !data}
    <div class="loading">Загрузка…</div>
{:else}
    <div class="kpis">
        {#each [
            ['Занятость', Math.round((data.occupancy || 0) * 1000) / 10 + '%'],
            ['ADR', fmtShortRub(data.adr)],
            ['RevPAR', fmtShortRub(data.revpar)],
            ['Ср. ночи', (data.avg_nights || 0).toFixed(1)]
        ] as [lbl, val]}
            <Card pad={14}>
                <div class="eyebrow">{lbl}</div>
                <div class="val">{val}</div>
            </Card>
        {/each}
    </div>

    <Section title="Загрузка по квартирам">
        <div class="wrap">
            <Card pad={14}>
                {#if data.per_apartment.length === 0}
                    <div class="empty">Нет данных за период</div>
                {:else}
                    {#each data.per_apartment as a, i}
                        {@const pct = Math.round((a.util || 0) * 100)}
                        {@const color = pct > 80 ? 'var(--positive)' : pct > 65 ? 'var(--caution)' : 'var(--muted)'}
                        <div class="bar-row" class:last={i === data.per_apartment.length - 1}>
                            <span class="bar-name">{a.title}</span>
                            <div class="bar">
                                <div class="bar-fill" style:width="{pct}%" style:background={color}></div>
                            </div>
                            <span class="bar-pct">{pct}%</span>
                        </div>
                    {/each}
                {/if}
            </Card>
        </div>
    </Section>

    <div class="foot">
        <span class="eyebrow">ПЕРИОД</span>
        <span class="range">{data.from} → {data.to}</span>
    </div>
{/if}

<style>
    .tabs {
        padding: 0 20px 14px;
        display: flex;
        gap: 6px;
    }
    .tab {
        flex: 1;
        height: 32px;
        border-radius: 6px;
        background: var(--card);
        border: 1px solid var(--border);
        color: var(--ink2);
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
    }
    .tab.active {
        background: var(--ink);
        color: var(--bg);
        border-color: var(--ink);
    }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty { color: var(--faint); text-align: center; padding: 12px; }
    .kpis {
        padding: 0 20px 14px;
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
        font-weight: 500;
    }
    .val {
        font-family: var(--font-serif);
        font-size: 26px;
        line-height: 1;
        color: var(--ink);
        margin-top: 8px;
    }
    .wrap { padding: 0 20px 14px; }
    .bar-row {
        display: grid;
        grid-template-columns: 120px 1fr 44px;
        gap: 10px;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .bar-row.last { border-bottom: none; }
    .bar-name {
        font-size: 11px;
        color: var(--ink);
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .bar {
        height: 6px;
        background: var(--border-soft);
        border-radius: 3px;
        overflow: hidden;
    }
    .bar-fill { height: 100%; }
    .bar-pct {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
        text-align: right;
    }
    .foot {
        padding: 0 20px 24px;
        display: flex;
        gap: 10px;
        align-items: center;
    }
    .range {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--ink2);
    }
</style>
```

- [ ] **Step 2: Commit + build check**

```bash
git add frontend/src/routes/reports/+page.svelte
git commit -m "feat(frontend): /reports — период, KPI, загрузка per-apt"
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 4: `/finance` — Финансы с inline-формой добавления расхода

**Files:**
- Create: `frontend/src/routes/finance/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import { fmtShortRub, fmtRub, fmtMonth } from '$lib/format.js';

    const currentMonth = new Date().toISOString().slice(0, 7);

    let data = $state(null);
    let error = $state(null);
    let loading = $state(true);
    let addOpen = $state(false);
    let addAmount = $state('');
    let addCategory = $state('Уборка');
    let addDescription = $state('');
    let addDate = $state(new Date().toISOString().slice(0, 10));
    let addError = $state(null);

    const CATS = ['Уборка', 'ЖКХ', 'Ремонт', 'Комиссии', 'Прочее'];

    async function load() {
        loading = true;
        try {
            data = await api.get(`/finance/summary?month=${currentMonth}`);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function saveExpense() {
        addError = null;
        const amount = parseInt(addAmount, 10);
        if (!amount || amount <= 0) {
            addError = 'Сумма должна быть > 0';
            return;
        }
        try {
            await api.post('/expenses', {
                amount,
                category: addCategory,
                description: addDescription || null,
                occurred_at: addDate
            });
            addOpen = false;
            addAmount = '';
            addDescription = '';
            await load();
        } catch (e) {
            addError = e.message;
        }
    }

    onMount(load);

    // Мапим category → цвет для доната
    const CAT_COLORS = {
        'Уборка': 'var(--accent)',
        'ЖКХ': 'var(--positive)',
        'Ремонт': 'var(--caution)',
        'Комиссии': 'var(--info)'
    };
    function colorFor(cat) {
        return CAT_COLORS[cat] || 'var(--muted)';
    }
</script>

<PageHead title="Финансы" sub={fmtMonth(currentMonth)}
    back="Настройки" backOnClick={() => goto('/settings')}>
    {#snippet right()}
        <button class="add-expense" type="button" onclick={() => (addOpen = !addOpen)}>
            {addOpen ? '×' : '+'} расход
        </button>
    {/snippet}
</PageHead>

{#if addOpen}
    <div class="wrap">
        <Card pad={14}>
            <div class="form-grid">
                <label class="fl">
                    <span>Сумма ₽</span>
                    <input type="number" bind:value={addAmount} placeholder="4200" />
                </label>
                <label class="fl">
                    <span>Категория</span>
                    <select bind:value={addCategory}>
                        {#each CATS as c}<option value={c}>{c}</option>{/each}
                    </select>
                </label>
                <label class="fl full">
                    <span>Описание (опционально)</span>
                    <input type="text" bind:value={addDescription} placeholder="Лермонтова 58" />
                </label>
                <label class="fl">
                    <span>Дата</span>
                    <input type="date" bind:value={addDate} />
                </label>
            </div>
            {#if addError}<div class="form-err">{addError}</div>{/if}
            <div class="form-actions">
                <button class="save" type="button" onclick={saveExpense}>Сохранить</button>
            </div>
        </Card>
    </div>
{/if}

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !data}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Hero -->
    <div class="wrap">
        <div class="hero">
            <div class="hero-eyebrow">Чистая прибыль</div>
            <div class="hero-big">{fmtShortRub(data.net)}</div>
            <div class="hero-split">
                <div>
                    <div class="hero-label">Выручка</div>
                    <div class="hero-val">{fmtRub(data.revenue)}</div>
                </div>
                <div>
                    <div class="hero-label">Расходы</div>
                    <div class="hero-val">{fmtRub(data.expenses_total)}</div>
                </div>
            </div>
        </div>
    </div>

    {#if Object.keys(data.by_category).length > 0}
        <Section title="Расходы по категориям">
            <div class="wrap">
                <Card pad={14}>
                    {#each Object.entries(data.by_category) as [cat, amt], i}
                        {@const pct = data.expenses_total ? Math.round(amt / data.expenses_total * 100) : 0}
                        <div class="cat-row" class:last={i === Object.keys(data.by_category).length - 1}>
                            <span class="dot" style:background={colorFor(cat)}></span>
                            <span class="cat">{cat}</span>
                            <span class="amt">{fmtShortRub(amt)}</span>
                            <span class="pct">{pct}%</span>
                        </div>
                    {/each}
                </Card>
            </div>
        </Section>
    {/if}

    <Section title="Последние движения">
        <div class="wrap">
            {#if data.feed.length === 0}
                <Card pad={16}><div class="empty">Движений нет</div></Card>
            {:else}
                <Card pad={0}>
                    {#each data.feed as item, i}
                        <div class="feed-row" class:last={i === data.feed.length - 1}>
                            <div class="feed-icon" class:income={item.type === 'income'} class:expense={item.type === 'expense'}>
                                {item.type === 'income' ? '+' : '−'}
                            </div>
                            <div class="feed-body">
                                <div class="feed-label">{item.label}</div>
                                <div class="feed-date">{item.dt}</div>
                            </div>
                            <div class="feed-amt" class:pos={item.type === 'income'}>
                                {item.type === 'income' ? '+' : '−'} {fmtShortRub(item.amount)}
                            </div>
                        </div>
                    {/each}
                </Card>
            {/if}
        </div>
    </Section>
{/if}

<style>
    .add-expense {
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
    }
    .wrap { padding: 0 20px 14px; }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty { color: var(--faint); text-align: center; padding: 12px; }

    .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .fl { display: flex; flex-direction: column; gap: 4px; }
    .fl.full { grid-column: 1 / -1; }
    .fl span {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--faint);
    }
    .fl input, .fl select {
        height: 40px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .form-err { color: var(--danger); font-size: 12px; margin-top: 8px; }
    .form-actions { margin-top: 12px; display: flex; justify-content: flex-end; }
    .save {
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 10px 18px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }

    .hero {
        background: var(--ink);
        color: var(--bg);
        border-radius: 10px;
        padding: 18px;
    }
    .hero-eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--accent);
        letter-spacing: 0.1em;
    }
    .hero-big {
        font-family: var(--font-serif);
        font-size: 40px;
        line-height: 1;
        margin-top: 8px;
        letter-spacing: -0.5px;
    }
    .hero-split {
        display: flex;
        gap: 20px;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    .hero-label {
        font-family: var(--font-mono);
        font-size: 9px;
        opacity: 0.6;
        text-transform: uppercase;
    }
    .hero-val {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        margin-top: 4px;
    }
    .cat-row {
        display: grid;
        grid-template-columns: 10px 1fr auto 42px;
        gap: 8px;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
        font-size: 13px;
    }
    .cat-row.last { border-bottom: none; }
    .dot { width: 8px; height: 8px; border-radius: 2px; }
    .cat { color: var(--ink); }
    .amt {
        font-family: var(--font-mono);
        color: var(--muted);
    }
    .pct {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-align: right;
    }
    .feed-row {
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
    }
    .feed-row.last { border-bottom: none; }
    .feed-icon {
        width: 30px;
        height: 30px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 16px;
        font-weight: 700;
    }
    .feed-icon.income { background: var(--positive-bg); color: var(--positive); }
    .feed-icon.expense { background: var(--bg-subtle); color: var(--muted); }
    .feed-body { flex: 1; }
    .feed-label { font-size: 13px; font-weight: 600; color: var(--ink); }
    .feed-date {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }
    .feed-amt {
        font-family: var(--font-mono);
        font-size: 13px;
        font-weight: 600;
        color: var(--ink);
    }
    .feed-amt.pos { color: var(--positive); }
</style>
```

- [ ] **Step 2: Commit + build check**

```bash
git add frontend/src/routes/finance/+page.svelte
git commit -m "feat(frontend): /finance — hero, донат, фид + inline добавление расхода"
cd frontend && npm run build 2>&1 | tail -5
```

---

## Phase 2 — Detail pages

### Task 5: `/clients` — Список клиентов с алфавитом

**Files:**
- Create: `frontend/src/routes/clients/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Searchbar from '$lib/ui/Searchbar.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtDate } from '$lib/format.js';

    let clients = $state([]);
    let bookings = $state([]);
    let error = $state(null);
    let loading = $state(true);
    let query = $state('');

    onMount(async () => {
        try {
            const [c, b] = await Promise.all([
                api.get('/clients'),
                api.get('/bookings')
            ]);
            clients = c;
            bookings = b;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    const today = new Date().toISOString().slice(0, 10);

    function tagFor(c) {
        const mine = bookings.filter(b => b.client_id === c.id);
        const active = mine.find(b =>
            b.status === 'active' && b.check_in <= today && b.check_out > today
        );
        if (active) return { text: `Сейчас в ${active.apartment_title || 'квартире'}`, color: 'var(--accent)' };
        const todayIn = mine.find(b =>
            b.status !== 'cancelled' && b.check_in === today
        );
        if (todayIn) return { text: `Сегодня · заезд 14:00`, color: 'var(--positive)' };
        const done = mine.filter(b => b.status !== 'cancelled').length;
        if (done >= 3) return { text: `Постоянный · ${done} броней`, color: 'var(--accent)' };
        if (done > 0) return { text: `${done} бронь`, color: 'var(--muted)' };
        return null;
    }

    function lastVisit(c) {
        const mine = bookings
            .filter(b => b.client_id === c.id && b.status !== 'cancelled')
            .sort((a, b) => b.check_in.localeCompare(a.check_in));
        return mine[0] ? fmtDate(mine[0].check_in) : '';
    }

    const visible = $derived(
        query
            ? clients.filter(c =>
                (c.full_name || '').toLowerCase().includes(query.toLowerCase())
                || (c.phone || '').includes(query)
            )
            : clients
    );

    const byLetter = $derived.by(() => {
        const map = new Map();
        for (const c of visible) {
            const L = (c.full_name || '—')[0].toUpperCase();
            if (!map.has(L)) map.set(L, []);
            map.get(L).push(c);
        }
        return Array.from(map.entries())
            .map(([letter, items]) => ({
                letter,
                items: items.sort((a, b) => a.full_name.localeCompare(b.full_name, 'ru'))
            }))
            .sort((a, b) => a.letter.localeCompare(b.letter, 'ru'));
    });
</script>

<PageHead title="Клиенты" sub="{clients.length} всего"
    back="Настройки" backOnClick={() => goto('/settings')} />

<div class="wrap">
    <Searchbar bind:value={query} placeholder="Имя или телефон…" />
</div>

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else if visible.length === 0}
    <div class="empty">Никого не найдено</div>
{:else}
    {#each byLetter as group}
        <div class="group-wrap">
            <div class="letter">{group.letter}</div>
            <Card pad={0}>
                {#each group.items as c, i}
                    {@const tag = tagFor(c)}
                    <button class="row" class:last={i === group.items.length - 1} onclick={() => goto(`/clients/${c.id}`)} type="button">
                        <Avatar name={c.full_name} size={36} />
                        <div class="body">
                            <div class="name">{c.full_name}</div>
                            {#if tag}<div class="tag" style:color={tag.color}>{tag.text}</div>{/if}
                        </div>
                        <div class="last">{lastVisit(c)}</div>
                    </button>
                {/each}
            </Card>
        </div>
    {/each}
{/if}

<style>
    .wrap { padding: 0 20px 12px; }
    .loading, .empty { padding: 40px 20px; color: var(--faint); text-align: center; }
    .group-wrap { padding: 0 20px 14px; }
    .letter {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0 2px 6px;
        font-weight: 600;
    }
    .row {
        width: 100%;
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
        background: transparent;
        border-top: none;
        border-left: none;
        border-right: none;
        cursor: pointer;
        text-align: left;
    }
    .row.last { border-bottom: none; }
    .row:hover { background: var(--card-hi); }
    .body { flex: 1; min-width: 0; }
    .name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .tag {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-top: 2px;
    }
    .last {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
</style>
```

- [ ] **Step 2: Commit + build check**

```bash
git add frontend/src/routes/clients/+page.svelte
git commit -m "feat(frontend): /clients — алфавит, теги, поиск"
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 6: `/clients/[id]` — Карточка клиента

**Files:**
- Create: `frontend/src/routes/clients/[id]/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtShortRub, fmtDate } from '$lib/format.js';

    const clientId = $derived(parseInt(page.params.id, 10));

    let data = $state(null);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        loading = true;
        try {
            data = await api.get(`/clients/${clientId}`);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    function statusLabel(s) {
        return { active: 'сейчас', completed: 'закрыта', cancelled: 'отменена' }[s] || s;
    }
    function statusTone(s) {
        return { active: 'accent', completed: 'ok', cancelled: 'late' }[s] || 'info';
    }
</script>

<PageHead title={data ? data.full_name : 'Клиент'}
    sub={data ? `${data.stats.count} броней · ${fmtShortRub(data.stats.revenue)}` : ''}
    back="Клиенты" backOnClick={() => goto('/clients')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !data}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Профиль -->
    <div class="wrap">
        <Card pad={14}>
            <div class="top">
                <Avatar name={data.full_name} size={56} accent="var(--accent)" />
                <div class="top-body">
                    <div class="name">{data.full_name}</div>
                    <div class="phone">{data.phone}</div>
                    {#if data.source}<div class="src">источник: {data.source}</div>{/if}
                </div>
            </div>
            <div class="stats">
                {#each [
                    ['Броней', data.stats.count],
                    ['Ночей', data.stats.nights],
                    ['Выручка', fmtShortRub(data.stats.revenue)]
                ] as [lbl, val]}
                    <div class="stat">
                        <div class="stat-lbl">{lbl}</div>
                        <div class="stat-val">{val}</div>
                    </div>
                {/each}
            </div>
        </Card>
    </div>

    <!-- Быстрые действия -->
    <div class="actions">
        <a class="action" href={`tel:${data.phone.replace(/\s+/g, '')}`}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7 12.8 12.8 0 0 0 .7 2.8 2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5 12.8 12.8 0 0 0 2.8.7 2 2 0 0 1 1.7 2z" />
            </svg>
            <span>Позвонить</span>
        </a>
        <a class="action" href={`sms:${data.phone.replace(/\s+/g, '')}`}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>SMS</span>
        </a>
        <button class="action" type="button" onclick={() => goto(`/bookings/new?client_id=${data.id}`)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.7" stroke-linecap="round">
                <path d="M12 5v14M5 12h14" />
            </svg>
            <span>Бронь</span>
        </button>
    </div>

    <!-- История -->
    <Section title="История броней">
        <div class="wrap">
            {#if data.bookings.length === 0}
                <Card pad={14}><div class="empty">Броней не было</div></Card>
            {:else}
                <div class="history">
                    {#each data.bookings as b}
                        <button class="hist-row" onclick={() => goto(`/bookings/${b.id}`)} type="button">
                            <div class="hist-body">
                                <div class="hist-dates">{fmtDate(b.check_in)} → {fmtDate(b.check_out)}</div>
                                <div class="hist-apt">{b.apartment_title}</div>
                            </div>
                            <div class="hist-right">
                                <div class="hist-sum">{fmtRub(b.total_price)}</div>
                                <Chip tone={statusTone(b.status)}>{statusLabel(b.status)}</Chip>
                            </div>
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    </Section>

    {#if data.notes}
        <Section title="Заметка">
            <div class="wrap">
                <Card pad={14}>
                    <div class="note">{data.notes}</div>
                </Card>
            </div>
        </Section>
    {/if}
{/if}

<style>
    .wrap { padding: 0 20px 14px; }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty { color: var(--faint); text-align: center; padding: 8px; }

    .top { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
    .top-body { flex: 1; min-width: 0; }
    .name { font-family: var(--font-serif); font-size: 22px; color: var(--ink); letter-spacing: -0.3px; }
    .phone { font-family: var(--font-mono); font-size: 11px; color: var(--faint); margin-top: 4px; }
    .src { font-family: var(--font-mono); font-size: 10px; color: var(--muted); margin-top: 2px; }

    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .stat { text-align: center; padding: 10px 0; background: var(--bg-subtle); border-radius: 6px; }
    .stat-lbl { font-family: var(--font-mono); font-size: 10px; color: var(--faint); text-transform: uppercase; }
    .stat-val { font-family: var(--font-serif); font-size: 20px; color: var(--ink); margin-top: 2px; }

    .actions {
        padding: 0 20px 14px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
    }
    .action {
        padding: 12px 0;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        color: var(--ink);
        text-decoration: none;
        cursor: pointer;
        font-size: 11px;
        font-weight: 500;
    }
    .action:hover { background: var(--card-hi); text-decoration: none; }

    .history { display: flex; flex-direction: column; gap: 8px; }
    .hist-row {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: pointer;
        text-align: left;
        gap: 12px;
    }
    .hist-row:hover { background: var(--card-hi); }
    .hist-body { flex: 1; min-width: 0; }
    .hist-dates { font-size: 13px; font-weight: 600; color: var(--ink); }
    .hist-apt { font-family: var(--font-mono); font-size: 10px; color: var(--faint); margin-top: 2px; text-transform: uppercase; }
    .hist-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .hist-sum { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: var(--ink); }

    .note { font-size: 13px; color: var(--ink2); line-height: 1.5; }
</style>
```

- [ ] **Step 2: Commit + build check**

```bash
git add frontend/src/routes/clients/[id]/+page.svelte
git commit -m "feat(frontend): /clients/[id] — профиль, быстрые действия, история"
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 7: `/apartments/[id]` — Карточка квартиры

**Files:**
- Create: `frontend/src/routes/apartments/[id]/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, ApiError } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtShortRub, fmtDate, fmtNights, fmtMonth } from '$lib/format.js';

    const aptId = $derived(parseInt(page.params.id, 10));
    const currentMonth = new Date().toISOString().slice(0, 7);

    let apt = $state(null);
    let stats = $state(null);
    let bookings = $state([]);
    let clients = $state([]);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        loading = true;
        try {
            const [a, s, b, c] = await Promise.all([
                api.get(`/apartments/${aptId}`),
                api.get(`/apartments/${aptId}/stats?month=${currentMonth}`),
                api.get('/bookings'),
                api.get('/clients')
            ]);
            apt = a;
            stats = s;
            bookings = b.filter(bb => bb.apartment_id === aptId);
            clients = c;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    const today = new Date().toISOString().slice(0, 10);

    const currentGuest = $derived.by(() => {
        const b = bookings.find(x =>
            x.status === 'active' && x.check_in <= today && x.check_out > today
        );
        if (!b) return null;
        const client = clients.find(c => c.id === b.client_id);
        return { booking: b, client };
    });

    async function markClean() {
        try {
            await api.post(`/apartments/${aptId}/mark-clean`);
            await load();
        } catch (e) {
            error = e.message;
        }
    }
    async function markDirty() {
        try {
            await api.post(`/apartments/${aptId}/mark-dirty`);
            await load();
        } catch (e) {
            error = e.message;
        }
    }
</script>

<PageHead title={apt?.title ?? 'Квартира'} sub={apt?.address}
    back="Квартиры" backOnClick={() => goto('/apartments')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !apt}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Cover -->
    <div class="cover-wrap">
        {#if apt.cover_url}
            <img src={apt.cover_url} alt="" class="cover" />
        {:else}
            <div class="cover placeholder">
                {(apt.title || '?').slice(0, 2).toUpperCase()}
            </div>
        {/if}
        <div class="cover-chip">
            <Chip tone={currentGuest ? 'ok' : apt.needs_cleaning ? 'due' : 'draft'}>
                {currentGuest ? `Занята до ${fmtDate(currentGuest.booking.check_out)}` : apt.needs_cleaning ? 'Требует уборки' : 'Свободна'}
            </Chip>
        </div>
    </div>

    <!-- KPI -->
    {#if stats}
        <div class="kpis">
            {#each [
                ['Ночей', stats.nights, fmtMonth(currentMonth)],
                ['ADR', fmtShortRub(stats.adr), ''],
                ['Выручка', fmtShortRub(stats.revenue), Math.round((stats.utilization || 0) * 100) + '%']
            ] as [lbl, val, meta]}
                <div class="kpi">
                    <div class="kpi-lbl">{lbl}</div>
                    <div class="kpi-val">{val}</div>
                    {#if meta}<div class="kpi-meta">{meta}</div>{/if}
                </div>
            {/each}
        </div>
    {/if}

    <!-- Current guest -->
    {#if currentGuest}
        <Section title="Гость">
            <div class="wrap">
                <Card pad={14}>
                    <button class="guest" type="button" onclick={() => currentGuest.client && goto(`/clients/${currentGuest.client.id}`)}>
                        <Avatar name={currentGuest.client?.full_name || '?'} size={44} accent="var(--accent)" />
                        <div class="guest-body">
                            <div class="guest-name">{currentGuest.client?.full_name || '—'}</div>
                            <div class="guest-phone">{currentGuest.client?.phone || ''}</div>
                        </div>
                    </button>
                    <div class="guest-range">
                        <span>{fmtDate(currentGuest.booking.check_in)} → {fmtDate(currentGuest.booking.check_out)}</span>
                        <span class="guest-sum">{fmtNights(currentGuest.booking.check_in, currentGuest.booking.check_out)} · {fmtRub(currentGuest.booking.total_price)}</span>
                    </div>
                </Card>
            </div>
        </Section>
    {/if}

    <!-- Характеристики -->
    <Section title="Характеристики">
        <div class="wrap">
            <Card pad={0}>
                {#each [
                    ['Тип', apt.rooms || '—'],
                    ['Площадь', apt.area_m2 ? apt.area_m2 + ' м²' : '—'],
                    ['Этаж', apt.floor || '—'],
                    ['Район', apt.district || '—'],
                    ['Цена/ночь', fmtRub(apt.price_per_night)],
                    ['Нужна уборка', apt.needs_cleaning ? 'Да' : 'Нет']
                ] as [k, v], i, arr}
                    <div class="ch-row" class:last={i === 5}>
                        <span class="ch-key">{k}</span>
                        <span class="ch-val">{v}</span>
                    </div>
                {/each}
            </Card>
        </div>
    </Section>

    <!-- Actions -->
    <div class="actions">
        {#if apt.needs_cleaning}
            <button class="primary" type="button" onclick={markClean}>Закрыть уборку ✓</button>
        {:else}
            <button class="ghost" type="button" onclick={markDirty}>Пометить грязной</button>
        {/if}
    </div>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .wrap { padding: 0 20px 14px; }
    .cover-wrap {
        margin: 0 20px 16px;
        height: 170px;
        border-radius: 10px;
        overflow: hidden;
        position: relative;
        background: var(--bg-subtle);
    }
    .cover {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .cover.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 34px;
        font-weight: 700;
        color: var(--faint);
    }
    .cover-chip {
        position: absolute;
        top: 12px;
        left: 12px;
    }

    .kpis {
        padding: 0 20px 14px;
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--card);
        margin: 0 20px 16px;
        overflow: hidden;
    }
    .kpi {
        padding: 12px 10px;
        text-align: center;
        border-right: 1px solid var(--border);
    }
    .kpi:last-child { border-right: none; }
    .kpi-lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--faint);
    }
    .kpi-val {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        margin-top: 4px;
        color: var(--ink);
    }
    .kpi-meta {
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        margin-top: 2px;
    }

    .guest {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        background: transparent;
        border: none;
        padding: 0 0 12px;
        cursor: pointer;
        text-align: left;
    }
    .guest-body { flex: 1; min-width: 0; }
    .guest-name { font-size: 15px; font-weight: 600; color: var(--ink); }
    .guest-phone { font-family: var(--font-mono); font-size: 11px; color: var(--faint); margin-top: 2px; }
    .guest-range {
        display: flex;
        justify-content: space-between;
        padding: 10px 12px;
        background: var(--bg-subtle);
        border-radius: 6px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
    }
    .guest-sum { color: var(--ink); font-weight: 600; }

    .ch-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-soft);
    }
    .ch-row.last { border-bottom: none; }
    .ch-key {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--faint);
        text-transform: uppercase;
    }
    .ch-val { font-size: 13px; color: var(--ink); font-weight: 500; }

    .actions {
        padding: 0 20px 24px;
        display: flex;
        gap: 10px;
    }
    .primary, .ghost {
        flex: 1;
        height: 46px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
```

- [ ] **Step 2: Commit + build**

```bash
git add frontend/src/routes/apartments/[id]/+page.svelte
git commit -m "feat(frontend): /apartments/[id] — карточка с KPI, гостем, характеристиками"
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 8: `/bookings/[id]` — Карточка брони

**Files:**
- Create: `frontend/src/routes/bookings/[id]/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtDate, fmtDateFull, fmtNights } from '$lib/format.js';

    const bookingId = $derived(parseInt(page.params.id, 10));

    let booking = $state(null);
    let client = $state(null);
    let apt = $state(null);
    let visitsCount = $state(0);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        loading = true;
        try {
            booking = await api.get(`/bookings/${bookingId}`);
            const [c, a] = await Promise.all([
                api.get(`/clients/${booking.client_id}`),
                api.get(`/apartments/${booking.apartment_id}`)
            ]);
            client = c;
            apt = a;
            visitsCount = c.stats?.count || 0;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    async function complete() {
        if (!confirm('Зафиксировать бронь как закрытую?')) return;
        try {
            await api.patch(`/bookings/${bookingId}`, { status: 'completed' });
            await load();
        } catch (e) {
            error = e.message;
        }
    }

    async function cancel() {
        if (!confirm('Отменить бронь?')) return;
        try {
            await api.patch(`/bookings/${bookingId}`, { status: 'cancelled' });
            await load();
        } catch (e) {
            error = e.message;
        }
    }

    function statusLabel(s) {
        return { active: 'активная', completed: 'закрыта', cancelled: 'отменена' }[s] || s;
    }
    function statusTone(s) {
        return { active: 'ok', completed: 'ok', cancelled: 'late' }[s] || 'info';
    }

    const nights = $derived(booking ? Math.round((new Date(booking.check_out) - new Date(booking.check_in)) / 86400000) : 0);
    const perNight = $derived(booking && nights ? Math.round(booking.total_price / nights) : 0);
</script>

<PageHead title={booking ? `Бронь #${booking.id}` : 'Бронь'}
    sub={booking ? (client?.source || 'Без источника') : ''}
    back="Брони" backOnClick={() => goto('/bookings')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !booking}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Основное -->
    <div class="wrap">
        <Card pad={14}>
            <div class="chip-row">
                <Chip tone={statusTone(booking.status)}>{statusLabel(booking.status)}</Chip>
                <span class="nights">{fmtNights(booking.check_in, booking.check_out)}</span>
            </div>
            <div class="dates">
                <div class="date-block">
                    <div class="dt-lbl">Заезд</div>
                    <div class="dt-val">{fmtDate(booking.check_in)}<span class="dt-time">14:00</span></div>
                </div>
                <svg class="arrow" width="18" height="12" viewBox="0 0 18 12" fill="none">
                    <path d="M1 6h16m0 0l-4-4m4 4l-4 4" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" />
                </svg>
                <div class="date-block right">
                    <div class="dt-lbl">Выезд</div>
                    <div class="dt-val">{fmtDate(booking.check_out)}<span class="dt-time">12:00</span></div>
                </div>
            </div>
        </Card>
    </div>

    <!-- Apartment -->
    <Section title="Квартира">
        <div class="wrap">
            <button class="apt-card" onclick={() => goto(`/apartments/${booking.apartment_id}`)} type="button">
                {#if apt?.cover_url}
                    <img src={apt.cover_url} alt="" class="apt-thumb" />
                {:else}
                    <div class="apt-thumb placeholder">
                        {(apt?.title || '?').slice(0, 2).toUpperCase()}
                    </div>
                {/if}
                <div class="apt-info">
                    <div class="apt-t">{apt?.title || booking.apartment_title}</div>
                    <div class="apt-meta">
                        {apt?.rooms || ''}
                        {#if apt?.area_m2}· {apt.area_m2} м²{/if}
                        {#if apt?.district} · {apt.district}{/if}
                    </div>
                </div>
            </button>
        </div>
    </Section>

    <!-- Guest -->
    <Section title="Гость">
        <div class="wrap">
            <button class="guest-card" onclick={() => goto(`/clients/${booking.client_id}`)} type="button">
                <Avatar name={client?.full_name || '?'} size={40} accent="var(--accent)" />
                <div class="guest-info">
                    <div class="guest-name">{client?.full_name || booking.client_name}</div>
                    <div class="guest-phone">
                        {client?.phone || ''}
                        {#if visitsCount > 0} · {visitsCount}-й визит{/if}
                    </div>
                </div>
            </button>
        </div>
    </Section>

    <!-- Расчёт -->
    <Section title="Расчёт">
        <div class="wrap">
            <Card pad={0}>
                <div class="calc-row">
                    <span>{nights} ночи × {fmtRub(perNight)}</span>
                    <span class="calc-num">{fmtRub(booking.total_price)}</span>
                </div>
            </Card>
        </div>
    </Section>

    {#if booking.notes}
        <Section title="Заметка">
            <div class="wrap"><Card pad={14}><div class="note">{booking.notes}</div></Card></div>
        </Section>
    {/if}

    <!-- Actions -->
    <div class="actions">
        {#if booking.status === 'active'}
            <button class="ghost" type="button" onclick={cancel}>Отменить</button>
            <button class="primary" type="button" onclick={complete}>Закрыть бронь →</button>
        {:else}
            <div class="closed">{statusLabel(booking.status).toUpperCase()}</div>
        {/if}
    </div>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .wrap { padding: 0 20px 14px; }
    .chip-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .nights {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .dates {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .date-block { flex: 1; }
    .date-block.right { text-align: right; }
    .dt-lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
    }
    .dt-val {
        font-family: var(--font-serif);
        font-size: 22px;
        color: var(--ink);
        margin-top: 4px;
    }
    .dt-time {
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 12px;
        margin-left: 6px;
    }
    .arrow { flex-shrink: 0; }

    .apt-card, .guest-card {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: left;
        cursor: pointer;
    }
    .apt-card:hover, .guest-card:hover { background: var(--card-hi); }
    .apt-thumb {
        width: 60px;
        height: 60px;
        border-radius: 6px;
        object-fit: cover;
        background: var(--bg-subtle);
    }
    .apt-thumb.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 14px;
        color: var(--faint);
        font-weight: 600;
    }
    .apt-info { flex: 1; min-width: 0; }
    .apt-t { font-size: 14px; font-weight: 600; color: var(--ink); }
    .apt-meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 3px;
        text-transform: uppercase;
    }

    .guest-info { flex: 1; min-width: 0; }
    .guest-name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .guest-phone {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }

    .calc-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 14px;
        font-size: 13px;
    }
    .calc-row span:first-child { color: var(--muted); }
    .calc-num {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
    }

    .note { font-size: 13px; color: var(--ink2); line-height: 1.5; }

    .actions {
        padding: 4px 20px 24px;
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 10px;
    }
    .primary, .ghost {
        height: 46px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
    .closed {
        grid-column: 1 / -1;
        padding: 14px;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
        letter-spacing: 0.08em;
        background: var(--bg-subtle);
        border-radius: 6px;
    }
</style>
```

- [ ] **Step 2: Commit + build**

```bash
git add frontend/src/routes/bookings/[id]/+page.svelte
git commit -m "feat(frontend): /bookings/[id] — детальная + actions (закрыть/отменить)"
cd frontend && npm run build 2>&1 | tail -5
```

---

## Phase 3 — Creation forms

### Task 9: `/apartments/new` — Декоративный парсер + форма

**Files:**
- Create: `frontend/src/routes/apartments/new/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';

    let url = $state('');
    let title = $state('');
    let address = $state('');
    let rooms = $state('2-комн');
    let area = $state('');
    let floor = $state('');
    let district = $state('');
    let price = $state('');
    let coverUrl = $state('');
    let ownerPhone = $state('');
    let saving = $state(false);
    let error = $state(null);

    const ROOMS_OPTIONS = ['Студия', '1-комн', '2-комн', '3+'];

    async function save() {
        error = null;
        if (!title || !address || !price) {
            error = 'Заполни название, адрес и цену';
            return;
        }
        const priceNum = parseInt(price, 10);
        if (!priceNum || priceNum <= 0) {
            error = 'Цена должна быть > 0';
            return;
        }
        saving = true;
        try {
            const payload = {
                title,
                address,
                price_per_night: priceNum
            };
            if (rooms) payload.rooms = rooms;
            if (area) payload.area_m2 = parseInt(area, 10);
            if (floor) payload.floor = floor;
            if (district) payload.district = district;
            if (coverUrl) payload.cover_url = coverUrl;
            const result = await api.post('/apartments', payload);
            goto(`/apartments/${result.id}`);
        } catch (e) {
            error = e.message;
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новая квартира" sub="Заполни или вставь ссылку с площадки"
    back="Отмена" backOnClick={() => goto('/apartments')} />

<!-- URL paste (декоративно) -->
<div class="wrap">
    <div class="eyebrow">Ссылка на объявление</div>
    <input class="url-field" bind:value={url} placeholder="https://doska.ykt.ru/board/..." />
    <div class="hint">Поддерживается: <span class="mono">Доска.якт · Юла</span>. Парсер не реализован — заполни поля руками.</div>
</div>

<!-- Source chips -->
<div class="wrap">
    <div class="sources">
        {#each [['Доска.якт', 'doska.ykt.ru'], ['Юла', 'youla.ru']] as [name, host]}
            <div class="source">
                <div class="source-init">{name[0]}</div>
                <div class="source-body">
                    <div class="source-name">{name}</div>
                    <div class="source-host">{host}</div>
                </div>
            </div>
        {/each}
    </div>
</div>

<!-- Form -->
<Section title="Поля квартиры">
    <div class="wrap">
        <Card pad={14}>
            <div class="form">
                <label>
                    <span>Название*</span>
                    <input bind:value={title} placeholder="Лермонтова 58/24" />
                </label>
                <label class="full">
                    <span>Адрес*</span>
                    <input bind:value={address} placeholder="ул. Лермонтова, 58, кв. 24" />
                </label>
                <label>
                    <span>Тип</span>
                    <select bind:value={rooms}>
                        {#each ROOMS_OPTIONS as r}<option value={r}>{r}</option>{/each}
                    </select>
                </label>
                <label>
                    <span>Площадь м²</span>
                    <input type="number" bind:value={area} placeholder="52" />
                </label>
                <label>
                    <span>Этаж</span>
                    <input bind:value={floor} placeholder="3/5" />
                </label>
                <label>
                    <span>Район</span>
                    <input bind:value={district} placeholder="Сайсары" />
                </label>
                <label>
                    <span>Цена/ночь ₽*</span>
                    <input type="number" bind:value={price} placeholder="4280" />
                </label>
                <label class="full">
                    <span>URL обложки (одна картинка)</span>
                    <input bind:value={coverUrl} placeholder="https://..." />
                </label>
            </div>
        </Card>
    </div>
</Section>

<Section title="Собственник (визуально — не сохраняется)">
    <div class="wrap">
        <Card pad={14}>
            <input bind:value={ownerPhone} placeholder="Телефон собственника" class="owner-input" />
        </Card>
    </div>
</Section>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="actions">
    <button class="ghost" type="button" onclick={() => goto('/apartments')} disabled={saving}>Отмена</button>
    <button class="primary" type="button" onclick={save} disabled={saving}>
        {saving ? 'Сохраняю…' : 'Сохранить →'}
    </button>
</div>

<style>
    .wrap { padding: 0 20px 14px; }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        margin-bottom: 8px;
    }
    .url-field {
        width: 100%;
        height: 48px;
        border: 1.5px solid var(--accent);
        background: var(--card);
        border-radius: 8px;
        padding: 0 14px;
        font-family: var(--font-mono);
        font-size: 12px;
        color: var(--ink);
    }
    .hint {
        margin-top: 8px;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .mono { color: var(--muted); }

    .sources {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .source {
        padding: 12px;
        border: 1px solid var(--border);
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 10px;
        background: var(--card);
    }
    .source-init {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: var(--bg-subtle);
        color: var(--ink);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-weight: 700;
        font-size: 12px;
    }
    .source-body { flex: 1; }
    .source-name { font-size: 13px; font-weight: 600; color: var(--ink); }
    .source-host {
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        margin-top: 1px;
    }

    .form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .form .full { grid-column: 1 / -1; }
    .form label { display: flex; flex-direction: column; gap: 4px; }
    .form label span {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .form input, .form select {
        height: 42px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .owner-input {
        width: 100%;
        height: 42px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }

    .actions {
        padding: 8px 20px 24px;
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 10px;
    }
    .primary, .ghost {
        height: 50px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
```

- [ ] **Step 2: Commit + build**

```bash
git add frontend/src/routes/apartments/new/+page.svelte
git commit -m "feat(frontend): /apartments/new — URL-декор + форма, POST /apartments"
cd frontend && npm run build 2>&1 | tail -5
```

---

### Task 10: `/bookings/new` — Форма создания брони

**Files:**
- Create: `frontend/src/routes/bookings/new/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Searchbar from '$lib/ui/Searchbar.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtNights } from '$lib/format.js';

    // Quick-param support: /bookings/new?client_id=N&apartment_id=M
    const preClientId = $derived(parseInt(page.url.searchParams.get('client_id') || '', 10) || null);
    const preApartmentId = $derived(parseInt(page.url.searchParams.get('apartment_id') || '', 10) || null);

    let apartments = $state([]);
    let clients = $state([]);
    let error = $state(null);
    let saving = $state(false);

    let apartmentId = $state(null);
    let clientId = $state(null);
    let checkIn = $state('');
    let checkOut = $state('');
    let totalPrice = $state('');
    let notes = $state('');
    let clientQuery = $state('');

    // Inline client creation
    let createOpen = $state(false);
    let newName = $state('');
    let newPhone = $state('');
    let newSource = $state('Прямая');

    onMount(async () => {
        try {
            const [a, c] = await Promise.all([
                api.get('/apartments'),
                api.get('/clients')
            ]);
            apartments = a;
            clients = c;
            if (preApartmentId) apartmentId = preApartmentId;
            if (preClientId) clientId = preClientId;
        } catch (e) {
            error = e.message;
        }
    });

    const apt = $derived(apartments.find(a => a.id === apartmentId) || null);
    const client = $derived(clients.find(c => c.id === clientId) || null);

    const nights = $derived.by(() => {
        if (!checkIn || !checkOut) return 0;
        return Math.round((new Date(checkOut) - new Date(checkIn)) / 86400000);
    });

    // Авто-пересчёт цены при смене дат/квартиры (если пользователь не редактировал руками)
    let priceManuallyEdited = $state(false);
    $effect(() => {
        if (priceManuallyEdited) return;
        if (apt && nights > 0) {
            totalPrice = String(apt.price_per_night * nights);
        }
    });

    const visibleClients = $derived(
        clientQuery
            ? clients.filter(c =>
                (c.full_name || '').toLowerCase().includes(clientQuery.toLowerCase())
                || (c.phone || '').includes(clientQuery)
            ).slice(0, 6)
            : clients.slice(-5).reverse()
    );

    async function createClient() {
        if (!newName || !newPhone) {
            error = 'Имя и телефон обязательны';
            return;
        }
        try {
            const c = await api.post('/clients', {
                full_name: newName,
                phone: newPhone,
                source: newSource || null
            });
            clients = [...clients, c];
            clientId = c.id;
            createOpen = false;
            newName = '';
            newPhone = '';
        } catch (e) {
            error = e.message;
        }
    }

    async function save() {
        error = null;
        if (!apartmentId) return (error = 'Выбери квартиру');
        if (!clientId) return (error = 'Выбери гостя');
        if (!checkIn || !checkOut) return (error = 'Укажи даты');
        const price = parseInt(totalPrice, 10);
        if (!price || price <= 0) return (error = 'Сумма должна быть > 0');
        if (new Date(checkOut) <= new Date(checkIn)) return (error = 'Выезд должен быть позже заезда');

        saving = true;
        try {
            const result = await api.post('/bookings', {
                apartment_id: apartmentId,
                client_id: clientId,
                check_in: checkIn,
                check_out: checkOut,
                total_price: price,
                notes: notes || null
            });
            goto(`/bookings/${result.id}`);
        } catch (e) {
            error = e.message;
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новая бронь" sub="Квартира → даты → гость → сумма"
    back="Отмена" backOnClick={() => goto('/bookings')} />

<!-- Apartment picker -->
<Section title="Квартира">
    <div class="wrap">
        {#if apt}
            <button class="selected" type="button" onclick={() => (apartmentId = null)}>
                <div class="sel-label">
                    <div class="sel-title">{apt.title}</div>
                    <div class="sel-meta">{apt.address}</div>
                </div>
                <span class="change">Сменить</span>
            </button>
        {:else}
            <div class="apt-list">
                {#each apartments as a}
                    <button class="pick" onclick={() => (apartmentId = a.id)} type="button">
                        <div class="pick-t">{a.title}</div>
                        <div class="pick-m">{a.address} · {fmtRub(a.price_per_night)}/ноч</div>
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</Section>

<!-- Dates -->
<Section title="Даты">
    <div class="wrap">
        <Card pad={14}>
            <div class="dates-form">
                <label>
                    <span>Заезд · 14:00</span>
                    <input type="date" bind:value={checkIn} />
                </label>
                <label>
                    <span>Выезд · 12:00</span>
                    <input type="date" bind:value={checkOut} />
                </label>
            </div>
            {#if nights > 0}
                <div class="nights-info">
                    <span>{fmtNights(checkIn, checkOut)}</span>
                </div>
            {/if}
        </Card>
    </div>
</Section>

<!-- Guest picker -->
<Section title="Гость">
    <div class="wrap">
        {#if client}
            <button class="selected" type="button" onclick={() => (clientId = null)}>
                <Avatar name={client.full_name} size={36} />
                <div class="sel-label">
                    <div class="sel-title">{client.full_name}</div>
                    <div class="sel-meta">{client.phone}</div>
                </div>
                <span class="change">Сменить</span>
            </button>
        {:else}
            <Searchbar bind:value={clientQuery} placeholder="Поиск имя / телефон…" />
            <div class="guest-list">
                {#each visibleClients as c}
                    <button class="pick" onclick={() => (clientId = c.id)} type="button">
                        <Avatar name={c.full_name} size={30} />
                        <div>
                            <div class="pick-t">{c.full_name}</div>
                            <div class="pick-m">{c.phone}</div>
                        </div>
                    </button>
                {/each}
            </div>
            <button class="create-toggle" onclick={() => (createOpen = !createOpen)} type="button">
                {createOpen ? '× Свернуть' : '+ Создать нового'}
            </button>
            {#if createOpen}
                <Card pad={12}>
                    <div class="create-form">
                        <label><span>Имя</span><input bind:value={newName} /></label>
                        <label><span>Телефон</span><input bind:value={newPhone} /></label>
                        <label>
                            <span>Источник</span>
                            <select bind:value={newSource}>
                                <option>Доска.якт</option>
                                <option>Юла</option>
                                <option>Прямая</option>
                            </select>
                        </label>
                        <button class="primary small" type="button" onclick={createClient}>Добавить</button>
                    </div>
                </Card>
            {/if}
        {/if}
    </div>
</Section>

<!-- Сумма -->
{#if apt && nights > 0}
    <Section title="Сумма">
        <div class="wrap">
            <Card pad={14}>
                <div class="calc">
                    <span>{nights} × {fmtRub(apt.price_per_night)} ночь</span>
                    <input
                        type="number"
                        class="total"
                        bind:value={totalPrice}
                        oninput={() => (priceManuallyEdited = true)}
                    />
                </div>
                <div class="calc-hint">ручное изменение переопределяет авто-расчёт</div>
            </Card>
        </div>
    </Section>
{/if}

<!-- Заметка -->
<Section title="Заметка (опционально)">
    <div class="wrap">
        <textarea class="notes" bind:value={notes} placeholder="…"></textarea>
    </div>
</Section>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="actions">
    <button class="ghost" type="button" onclick={() => goto('/bookings')} disabled={saving}>Отмена</button>
    <button class="primary" type="button" onclick={save} disabled={saving}>
        {saving ? 'Сохраняю…' : 'Создать бронь →'}
    </button>
</div>

<style>
    .wrap { padding: 0 20px 14px; }

    .selected {
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
    .sel-label { flex: 1; min-width: 0; }
    .sel-title { font-size: 14px; font-weight: 600; color: var(--ink); }
    .sel-meta { font-family: var(--font-mono); font-size: 10px; color: var(--faint); margin-top: 2px; text-transform: uppercase; }
    .change { font-size: 12px; color: var(--accent); font-weight: 500; }

    .apt-list, .guest-list { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
    .pick {
        width: 100%;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 10px 12px;
        display: flex;
        align-items: center;
        gap: 10px;
        text-align: left;
        cursor: pointer;
    }
    .pick:hover { background: var(--card-hi); }
    .pick-t { font-size: 13px; font-weight: 600; color: var(--ink); }
    .pick-m { font-family: var(--font-mono); font-size: 10px; color: var(--faint); margin-top: 2px; }

    .dates-form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .dates-form label { display: flex; flex-direction: column; gap: 4px; }
    .dates-form label span {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .dates-form input {
        height: 42px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .nights-info {
        margin-top: 12px;
        padding: 10px 12px;
        background: var(--bg-subtle);
        border-radius: 6px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--ink);
        font-weight: 600;
    }

    .create-toggle {
        margin-top: 10px;
        width: 100%;
        padding: 10px;
        background: transparent;
        border: 1px dashed var(--border);
        color: var(--muted);
        font-size: 12px;
        border-radius: 6px;
        cursor: pointer;
    }
    .create-form {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .create-form label { display: flex; flex-direction: column; gap: 4px; }
    .create-form label span {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .create-form input, .create-form select {
        height: 38px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .small { height: 40px !important; margin-top: 4px; }

    .calc {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
    }
    .calc span {
        font-family: var(--font-mono);
        font-size: 12px;
        color: var(--muted);
    }
    .total {
        width: 130px;
        height: 40px;
        background: var(--bg);
        border: 1.5px solid var(--accent);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-family: var(--font-mono);
        font-weight: 600;
        font-size: 14px;
        text-align: right;
    }
    .calc-hint {
        margin-top: 6px;
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        text-transform: uppercase;
    }

    .notes {
        width: 100%;
        min-height: 60px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 10px;
        color: var(--ink);
        font-family: var(--font-sans);
        font-size: 13px;
        resize: vertical;
    }

    .actions {
        padding: 8px 20px 24px;
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 10px;
    }
    .primary, .ghost {
        height: 50px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
```

- [ ] **Step 2: Commit + build**

```bash
git add frontend/src/routes/bookings/new/+page.svelte
git commit -m "feat(frontend): /bookings/new — один экран (квартира/даты/гость/сумма)"
cd frontend && npm run build 2>&1 | tail -5
```

---

## Phase 4 — Calendar

### Task 11: `/calendar` — Шахматка 14 дней

**Files:**
- Create: `frontend/src/routes/calendar/+page.svelte`

- [ ] **Step 1: Создать файл**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';

    let apartments = $state([]);
    let calendar = $state([]);
    let error = $state(null);
    let loading = $state(true);

    const today = new Date();
    const from = today.toISOString().slice(0, 10);
    const toDate = new Date(today);
    toDate.setDate(toDate.getDate() + 14);
    const to = toDate.toISOString().slice(0, 10);

    const days = Array.from({ length: 14 }, (_, i) => {
        const d = new Date(today);
        d.setDate(d.getDate() + i);
        return d;
    });

    onMount(async () => {
        try {
            const [apts, cal] = await Promise.all([
                api.get('/apartments'),
                api.get(`/bookings/calendar?from=${from}&to=${to}`)
            ]);
            apartments = apts;
            calendar = cal;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    const todayISO = from;
    const COL_W = 24;
    const ROW_H = 36;

    function bookingsFor(aptId) {
        const entry = calendar.find(c => c.apartment_id === aptId);
        return entry ? entry.bookings : [];
    }

    // position: days from `from` date
    function startCol(b) {
        const ci = new Date(b.check_in);
        const start = new Date(from);
        return Math.max(0, Math.round((ci - start) / 86400000));
    }
    function widthCols(b) {
        const ci = new Date(Math.max(new Date(b.check_in), new Date(from)));
        const co = new Date(Math.min(new Date(b.check_out), new Date(to)));
        return Math.max(1, Math.round((co - ci) / 86400000));
    }
    function tone(b) {
        if (b.status === 'completed') return 'var(--positive)';
        return 'var(--accent)';
    }
</script>

<PageHead title="Шахматка" sub="{apartments.length} кв · 14 дней"
    back="Настройки" backOnClick={() => goto('/settings')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else}
    <div class="grid-wrap">
        <div class="grid" style:--col-w="{COL_W}px" style:--row-h="{ROW_H}px">
            <!-- header -->
            <div class="header-row">
                <div class="name-col">Апрель</div>
                {#each days as d, i}
                    {@const dt = d.toISOString().slice(0, 10)}
                    {@const isToday = dt === todayISO}
                    {@const weekend = d.getDay() === 0 || d.getDay() === 6}
                    <div class="day-cell" class:today={isToday} class:weekend>
                        {d.getDate()}
                    </div>
                {/each}
            </div>
            <!-- rows -->
            {#each apartments as a, ai}
                <div class="row">
                    <div class="name-col">{a.title}</div>
                    {#each days as d, i}
                        {@const dt = d.toISOString().slice(0, 10)}
                        <div class="cell" class:today={dt === todayISO}></div>
                    {/each}
                    {#each bookingsFor(a.id) as b}
                        <div
                            class="bar"
                            style:left="calc(110px + {startCol(b)} * var(--col-w) + 2px)"
                            style:width="calc({widthCols(b)} * var(--col-w) - 4px)"
                            style:background={tone(b)}
                            title={`${b.client_name} · ${b.check_in} → ${b.check_out}`}
                            onclick={() => goto(`/bookings/${b.id}`)}
                            role="button"
                            tabindex="0"
                            onkeydown={(e) => { if (e.key === 'Enter') goto(`/bookings/${b.id}`); }}
                        >
                            <span class="bar-text">{b.client_name.split(' ')[0]}</span>
                        </div>
                    {/each}
                </div>
            {/each}
        </div>

        <div class="legend">
            <span class="leg-item"><span class="leg-dot" style:background="var(--accent)"></span>активная</span>
            <span class="leg-item"><span class="leg-dot" style:background="var(--positive)"></span>закрыта</span>
        </div>
    </div>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .grid-wrap {
        padding: 0 20px 24px;
        overflow-x: auto;
    }
    .grid {
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
        background: var(--card);
        min-width: calc(110px + 14 * var(--col-w));
    }
    .header-row, .row {
        display: grid;
        grid-template-columns: 110px repeat(14, var(--col-w));
        border-bottom: 1px solid var(--border-soft);
    }
    .row {
        height: var(--row-h);
        position: relative;
    }
    .row:last-child { border-bottom: none; }
    .header-row {
        background: var(--card-hi);
    }
    .name-col {
        padding: 8px 10px;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        border-right: 1px solid var(--border-soft);
        display: flex;
        align-items: center;
    }
    .row .name-col {
        font-family: var(--font-sans);
        font-size: 11px;
        color: var(--ink);
        font-weight: 500;
        text-transform: none;
        letter-spacing: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .day-cell, .cell {
        border-left: 1px solid var(--border-soft);
    }
    .day-cell {
        padding: 6px 0;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .day-cell.weekend { color: var(--muted); }
    .day-cell.today, .cell.today {
        background: var(--accent-bg);
        color: var(--accent);
        font-weight: 700;
    }
    .bar {
        position: absolute;
        top: 7px;
        height: calc(var(--row-h) - 14px);
        border-radius: 3px;
        opacity: 0.88;
        cursor: pointer;
        display: flex;
        align-items: center;
        padding: 0 4px;
        overflow: hidden;
    }
    .bar:hover { opacity: 1; }
    .bar-text {
        font-size: 9px;
        color: #fff;
        font-weight: 600;
        white-space: nowrap;
    }
    .legend {
        margin-top: 12px;
        display: flex;
        gap: 14px;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .leg-item { display: inline-flex; align-items: center; gap: 5px; }
    .leg-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
</style>
```

- [ ] **Step 2: Commit + build**

```bash
git add frontend/src/routes/calendar/+page.svelte
git commit -m "feat(frontend): /calendar — шахматка 14 дней"
cd frontend && npm run build 2>&1 | tail -5
```

---

## Phase 5 — Финал

### Task 12: Smoke-пробег + обновление статуса в спеке

- [ ] **Step 1: Полный build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```
Expected: `✓ built in …`, никаких ошибок.

- [ ] **Step 2: Smoke check через curl**

В терминале 1:
```bash
uv run --env-file .env uvicorn backend.main:app --port 8000 &
```
В терминале 2 (после 3 секунд):
```bash
cd frontend && npm run dev -- --port 5173 &
```
После 3-4 секунд:
```bash
for path in / /login /dev_auth /apartments /apartments/new /bookings /bookings/new /calendar /cleaning /clients /finance /reports /users /settings; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173$path)
  printf "%-20s → %s\n" "$path" "$code"
done
```
Expected: все 200.

Потом `pkill -f uvicorn; pkill -f "vite dev"`.

- [ ] **Step 3: Обновить статус в спеке**

В `docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md` — заменить:

```markdown
- [x] Backend (план 1/3) — готов 2026-04-21
- [x] Frontend foundation + core screens (план 2/3) — готов 2026-04-21
- [ ] Frontend remaining screens (план 3/3)
```

на:

```markdown
- [x] Backend (план 1/3) — готов 2026-04-21
- [x] Frontend foundation + core screens (план 2/3) — готов 2026-04-21
- [x] Frontend remaining screens (план 3/3) — готов 2026-04-21
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md
git commit -m "docs(spec): все три плана завершены"
```

---

## Готово

После выполнения этого плана весь дизайн из handoff-бандла реализован. Что именно доступно:

- `/` Сводка, `/calendar` шахматка
- `/apartments` список + `/apartments/new` парсер-декор + `/apartments/:id` карточка
- `/bookings` список + `/bookings/new` форма + `/bookings/:id` детальная
- `/cleaning` список уборок
- `/clients` список + `/clients/:id` карточка с историей
- `/finance` (revenue, expenses, доната, фид + inline-add расход)
- `/reports` (KPI, бары per-apt, период-табы)
- `/users` (owner-only)
- `/settings` (профиль, тема, ссылки в разделы, выход)
- `/login` декор + `/dev_auth` пикер

Полный спек реализован. Следующие улучшения — уже beyond scope.
