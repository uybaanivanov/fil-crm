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
