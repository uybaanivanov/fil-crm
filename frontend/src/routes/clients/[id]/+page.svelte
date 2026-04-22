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
                                <div class="hist-apt">
                                    {#if b.apartment_callsign}<span class="cs">{b.apartment_callsign}</span> · {/if}{b.apartment_title}
                                </div>
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
    .hist-apt .cs { color: var(--accent); font-weight: 600; }
    .hist-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .hist-sum { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: var(--ink); }

    .note { font-size: 13px; color: var(--ink2); line-height: 1.5; }
</style>
