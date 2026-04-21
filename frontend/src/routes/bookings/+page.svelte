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
