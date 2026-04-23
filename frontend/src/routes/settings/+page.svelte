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
    import { getCurrency, setCurrency, CURRENCIES } from '$lib/currency.js';
    import { fmtRole } from '$lib/format.js';

    let user = $state(null);
    let theme = $state('dark');
    let currency = $state('RUB');

    onMount(() => {
        user = getUser();
        theme = getTheme();
        currency = getCurrency();
    });

    function chooseCurrency(code) {
        currency = code;
        setCurrency(code); // внутри — location.reload, формат подтянется во всём аппе
    }

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
                <Avatar name={user.full_name} size={56} role={user.role} accent="var(--ink)" />
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

    <!-- Валюта -->
    <Section title="Валюта">
        <div class="wrap">
            <Card pad={14}>
                <div class="cur-head">
                    <div class="lbl">Отображение сумм</div>
                    <div class="hint">Курсы обновляются раз в день</div>
                </div>
                <div class="seg cur-seg">
                    {#each CURRENCIES as code}
                        <button class="seg-btn" class:active={currency === code} type="button" onclick={() => chooseCurrency(code)}>
                            {code}
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
    .cur-head { margin-bottom: 12px; }
    .cur-seg { grid-template-columns: repeat(3, 1fr); }
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
