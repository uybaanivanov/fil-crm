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
