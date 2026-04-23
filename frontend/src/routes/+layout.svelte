<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import TabBar from '$lib/ui/TabBar.svelte';
    import { getUser } from '$lib/auth.js';
    import { api } from '$lib/api.js';
    import { getCurrency, setCurrency, refreshRatesIfStale, CURRENCIES } from '$lib/currency.js';
    import '../app.css';

    let { children } = $props();
    let ready = $state(false);
    let user = $state(null);
    let cur = $state('RUB');
    let ratesRefreshed = false;

    // Пути, где TabBar скрыт (auth-flow) и guard'ы не действуют
    const PUBLIC = ['/login', '/dev_auth'];

    function isPublic(path) {
        return PUBLIC.some(p => path === p || path.startsWith(p + '/'));
    }

    onMount(() => {
        cur = getCurrency();
    });

    // Перечитываем сессию на каждой навигации — лэйаут в SPA не перемонтируется,
    // так что onMount после login→goto не сработает и TabBar остаётся скрыт.
    // Важно: работаем с локальной `u`, в $state `user` только пишем. Если читать user
    // в этом же эффекте — self-dep → effect_update_depth_exceeded.
    $effect(() => {
        const path = page.url.pathname;
        const u = getUser();
        if (!u && !isPublic(path)) {
            user = null;
            ready = true;
            goto('/login');
            return;
        }
        if (u && path === '/login') {
            user = u;
            goto(u.role === 'maid' ? '/cleaning' : '/');
            return;
        }
        if (u && !ratesRefreshed) {
            ratesRefreshed = true;
            refreshRatesIfStale(api);
        }
        user = u;
        ready = true;
    });

    let showTabs = $derived(user && !isPublic(page.url.pathname));

    function changeCurrency(e) {
        setCurrency(e.target.value);
    }
</script>

<select class="cur-switch" value={cur} onchange={changeCurrency}>
    {#each CURRENCIES as c}<option value={c}>{c}</option>{/each}
</select>

{#if ready}
    <div class="app-shell">
        <main class="app-main">
            {@render children?.()}
        </main>
        {#if showTabs}<TabBar />{/if}
    </div>
{/if}

<style>
.cur-switch {
    position: fixed; top: 8px; right: 8px; z-index: 100;
    width: auto;
    background: rgba(255,255,255,0.9);
    border: 1px solid var(--border, #ccc);
    border-radius: 6px; padding: 4px 8px;
    font-size: 12px; cursor: pointer;
}
</style>
