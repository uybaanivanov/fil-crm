<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import { fmtShortRub, fmtRub, fmtMonth } from '$lib/format.js';

    let user = $state(null);
    let data = $state(null);
    let error = $state(null);

    onMount(async () => {
        user = getUser();
        try {
            data = await api.get('/dashboard/summary');
        } catch (e) {
            error = e.message;
        }
    });

    const maxDaily = $derived(data ? Math.max(1, ...data.daily_series) : 1);
    const todayIdx = $derived(data ? (new Date().getDate() - 1) : 0);
</script>

<PageHead title="Доброе утро" sub={user?.full_name?.split(' ')[0] ?? ''} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if !data}
    <div class="loading">Загрузка…</div>
{:else}
    <div class="kpis">
        <Card pad={14}>
            <div class="eyebrow">Занято</div>
            <div class="num big">
                {data.occupancy.occupied}<span class="slash">/{data.occupancy.total}</span>
            </div>
        </Card>
        <Card pad={14}>
            <div class="eyebrow">Выручка · {fmtMonth(data.month)}</div>
            <div class="num big">{fmtShortRub(data.revenue_mtd)}</div>
            {#if data.revenue_prev_month > 0}
                {@const delta = Math.round(((data.revenue_mtd - data.revenue_prev_month) / data.revenue_prev_month) * 100)}
                <div class="delta" class:pos={delta >= 0} class:neg={delta < 0}>
                    {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)}% к {fmtMonth(data.month).split(' ')[0]}
                </div>
            {/if}
        </Card>
    </div>

    <Section title="Выручка — {fmtMonth(data.month)}">
        <div class="chart-wrap">
            <Card pad={14}>
                <svg viewBox="0 0 300 70" width="100%" height="70" preserveAspectRatio="none">
                    {#each data.daily_series as v, i}
                        {@const h = (v / maxDaily) * 64}
                        {@const isToday = i === todayIdx}
                        {@const isFuture = i > todayIdx}
                        <rect
                            x={i * (300 / data.daily_series.length) + 1}
                            y={70 - h}
                            width={Math.max(1, 300 / data.daily_series.length - 2)}
                            height={Math.max(0, h)}
                            fill={isToday ? 'var(--accent)' : isFuture ? 'var(--border-soft)' : 'var(--ink2)'}
                        />
                    {/each}
                </svg>
                <div class="chart-axis">
                    <span>1</span>
                    <span>10</span>
                    <span class="today">{todayIdx + 1} · СЕГ</span>
                    <span>{data.daily_series.length}</span>
                </div>
            </Card>
        </div>
    </Section>

    <Section title="Сегодня">
        <div class="events">
            {#if data.today_events.length === 0}
                <Card pad={16}>
                    <div class="empty">Событий нет</div>
                </Card>
            {:else}
                {#each data.today_events as ev}
                    <button class="event" type="button" onclick={() => goto(`/bookings/${ev.booking_id}`)}>
                        {#if ev.apartment_cover_url}
                            <img class="thumb" src={ev.apartment_cover_url} alt="" />
                        {:else}
                            <div class="thumb placeholder">
                                {(ev.apartment_callsign || ev.apartment_title || '?').slice(0, 2).toUpperCase()}
                            </div>
                        {/if}
                        <div class="event-body">
                            <div class="kind {ev.kind}">{ev.time} · {ev.client_name}</div>
                            <div class="addr">
                                {#if ev.apartment_callsign}<span class="callsign">{ev.apartment_callsign}</span> · {/if}
                                {ev.apartment_address}
                            </div>
                        </div>
                        <div class="event-right">
                            {#if ev.total_price != null}
                                <div class="amt">{fmtRub(ev.total_price)}</div>
                            {/if}
                            <Chip tone={ev.kind === 'check_in' ? 'ok' : 'draft'}>
                                {ev.kind === 'check_in' ? 'заезд' : 'выезд'}
                            </Chip>
                        </div>
                    </button>
                {/each}
            {/if}
        </div>
    </Section>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--muted); text-align: center; }
    .kpis {
        padding: 8px 20px 16px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .big {
        font-family: var(--font-serif);
        font-size: 32px;
        line-height: 1;
        margin-top: 8px;
        color: var(--ink);
    }
    .slash { font-size: 16px; color: var(--faint); font-family: var(--font-mono); }
    .delta {
        font-family: var(--font-mono);
        font-size: 10px;
        margin-top: 6px;
    }
    .delta.pos { color: var(--positive); }
    .delta.neg { color: var(--danger); }
    .chart-wrap { padding: 0 20px 16px; }
    .chart-axis {
        display: flex;
        justify-content: space-between;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 6px;
    }
    .chart-axis .today { color: var(--accent); }
    .events { padding: 0 20px; display: flex; flex-direction: column; gap: 8px; }
    .event {
        width: 100%;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 10px 12px;
        display: grid;
        grid-template-columns: 44px 1fr auto;
        gap: 10px;
        align-items: center;
        cursor: pointer;
        text-align: left;
    }
    .event:hover { background: var(--card-hi); }
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
    .callsign {
        color: var(--accent);
        font-weight: 600;
    }
    .kind { font-size: 13px; font-weight: 600; color: var(--ink); }
    .addr {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
        text-transform: uppercase;
    }
    .event-right { text-align: right; display: flex; flex-direction: column; gap: 4px; align-items: flex-end; }
    .amt {
        font-family: var(--font-mono);
        font-size: 12px;
        font-weight: 600;
        color: var(--ink);
    }
    .empty { color: var(--faint); text-align: center; padding: 12px; }
</style>
