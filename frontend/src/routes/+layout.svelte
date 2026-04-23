<script>
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import TabBar from '$lib/ui/TabBar.svelte';
    import { getUser } from '$lib/auth.js';
    import { api } from '$lib/api.js';
    import { refreshRatesIfStale } from '$lib/currency.js';
    import '../app.css';

    let { children } = $props();
    let ready = $state(false);
    let user = $state(null);
    let ratesRefreshed = false;

    // Пути, где TabBar скрыт (auth-flow) и guard'ы не действуют
    const PUBLIC = ['/login', '/dev_auth'];

    function isPublic(path) {
        return PUBLIC.some(p => path === p || path.startsWith(p + '/'));
    }

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
</script>

{#if ready}
    <div class="app-shell">
        <main class="app-main">
            {@render children?.()}
        </main>
        {#if showTabs}<TabBar />{/if}
    </div>
{/if}
