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
