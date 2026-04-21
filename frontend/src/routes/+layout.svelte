<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import favicon from '$lib/assets/favicon.svg';
    import { getUser, clearUser } from '$lib/auth.js';

    let { children } = $props();

    let user = $state(null);
    let ready = $state(false);

    onMount(() => {
        user = getUser();
        const path = page.url.pathname;
        if (!user && path !== '/login') {
            goto('/login');
            return;
        }
        if (user && path === '/login') {
            goto(user.role === 'maid' ? '/cleaning' : '/apartments');
            return;
        }
        ready = true;
    });

    function logout() {
        clearUser();
        user = null;
        goto('/login');
    }

    const NAV = {
        owner: [
            { href: '/apartments', label: 'Квартиры' },
            { href: '/clients',    label: 'Клиенты'  },
            { href: '/bookings',   label: 'Брони'    },
            { href: '/users',      label: 'Пользователи' }
        ],
        admin: [
            { href: '/apartments', label: 'Квартиры' },
            { href: '/clients',    label: 'Клиенты'  },
            { href: '/bookings',   label: 'Брони'    }
        ],
        maid: [
            { href: '/cleaning',   label: 'Уборка' }
        ]
    };

    let items = $derived(user ? NAV[user.role] || [] : []);
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

{#if ready}
    {#if user}
        <nav class="topbar">
            <span class="brand">fil-crm</span>
            {#each items as item}
                <a href={item.href} class:active={page.url.pathname === item.href}>{item.label}</a>
            {/each}
            <span class="spacer"></span>
            <span class="badge">{user.full_name} · {user.role}</span>
            <button onclick={logout}>Выход</button>
        </nav>
    {/if}
    <div class="container">
        {@render children?.()}
    </div>
{/if}
