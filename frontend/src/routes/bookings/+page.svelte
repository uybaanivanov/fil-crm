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
    let tab = $state('all');

    const PAGE_SIZE = 50;
    let visibleCount = $state(PAGE_SIZE);

    function setTab(v) {
        tab = v;
        visibleCount = PAGE_SIZE;
    }

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

    const events = $derived.by(() => {
        const out = [];
        for (const b of bookings) {
            if (b.status === 'cancelled' && tab !== 'cancelled') continue;
            if (tab === 'cancelled' && b.status !== 'cancelled') continue;
            if (tab === 'check_in')   out.push({ ...b, kind: 'check_in', date: b.check_in });
            else if (tab === 'check_out') out.push({ ...b, kind: 'check_out', date: b.check_out });
            else if (tab === 'cancelled') out.push({ ...b, kind: 'cancelled', date: b.check_in });
            else {
                out.push({ ...b, kind: 'check_in', date: b.check_in });
                out.push({ ...b, kind: 'check_out', date: b.check_out });
            }
        }
        out.sort((a, b) => b.date.localeCompare(a.date));
        return out;
    });

    const visibleEvents = $derived(events.slice(0, visibleCount));
    const hasMore = $derived(events.length > visibleCount);

    const groups = $derived.by(() => {
        const g = new Map();
        for (const e of visibleEvents) {
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
        <button class="tab" class:active={t.active} type="button" onclick={() => setTab(t.value)}>
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
                        {#if ev.apartment_cover_url}
                            <img class="thumb" src={ev.apartment_cover_url} alt="" />
                        {:else}
                            <div class="thumb placeholder">
                                {(ev.apartment_callsign || ev.apartment_title || '?').slice(0, 2).toUpperCase()}
                            </div>
                        {/if}
                        <div class="ev-body">
                            <div class="ev-head">
                                <span class="time">{ev.kind === 'check_in' ? '14:00' : '12:00'}</span>
                                <span class="kind {ev.kind}">
                                    {ev.kind === 'check_in' ? 'ЗАЕЗД' : 'ВЫЕЗД'}
                                </span>
                            </div>
                            <div class="name">{ev.client_name}</div>
                            <div class="meta">
                                {#if ev.apartment_callsign}<span class="cs">{ev.apartment_callsign}</span> · {/if}{ev.apartment_title} · {sourceOf(ev)}
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
    {#if hasMore}
        <div class="more">
            <button
                class="more-btn"
                type="button"
                onclick={() => (visibleCount += PAGE_SIZE)}
            >
                Показать ещё · {events.length - visibleCount} осталось
            </button>
        </div>
    {:else if events.length > PAGE_SIZE}
        <div class="more-done">Всё · {events.length}</div>
    {/if}
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
        grid-template-columns: 4px 44px 1fr auto;
        gap: 10px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 10px 12px;
        cursor: pointer;
        text-align: left;
        align-items: center;
    }
    .thumb {
        width: 44px;
        height: 44px;
        border-radius: 6px;
        object-fit: cover;
        background: var(--bg-subtle);
    }
    .thumb.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 12px;
        font-weight: 600;
        color: var(--faint);
    }
    .cs { color: var(--accent); font-weight: 600; }
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
    .more { padding: 6px 20px 24px; }
    .more-btn {
        width: 100%;
        height: 42px;
        background: var(--card);
        color: var(--ink);
        border: 1px solid var(--border);
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
    }
    .more-btn:hover { background: var(--card-hi); }
    .more-done {
        padding: 10px 20px 24px;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--faint);
    }
</style>
