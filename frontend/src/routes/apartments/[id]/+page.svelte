<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, ApiError } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtShortRub, fmtDate, fmtNights, fmtMonth } from '$lib/format.js';

    const aptId = $derived(parseInt(page.params.id, 10));
    const currentMonth = new Date().toISOString().slice(0, 7);

    let apt = $state(null);
    let stats = $state(null);
    let bookings = $state([]);
    let clients = $state([]);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        loading = true;
        try {
            const [a, s, b, c] = await Promise.all([
                api.get(`/apartments/${aptId}`),
                api.get(`/apartments/${aptId}/stats?month=${currentMonth}`),
                api.get('/bookings'),
                api.get('/clients')
            ]);
            apt = a;
            stats = s;
            bookings = b.filter(bb => bb.apartment_id === aptId);
            clients = c;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    const today = new Date().toISOString().slice(0, 10);

    const currentGuest = $derived.by(() => {
        const b = bookings.find(x =>
            x.status === 'active' && x.check_in <= today && x.check_out > today
        );
        if (!b) return null;
        const client = clients.find(c => c.id === b.client_id);
        return { booking: b, client };
    });

    async function markClean() {
        try {
            await api.post(`/apartments/${aptId}/mark-clean`);
            await load();
        } catch (e) {
            error = e.message;
        }
    }
    async function markDirty() {
        try {
            await api.post(`/apartments/${aptId}/mark-dirty`);
            await load();
        } catch (e) {
            error = e.message;
        }
    }
</script>

<PageHead title={apt?.title ?? 'Квартира'} sub={apt?.address}
    back="Квартиры" backOnClick={() => goto('/apartments')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !apt}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Cover -->
    <div class="cover-wrap">
        {#if apt.cover_url}
            <img src={apt.cover_url} alt="" class="cover" />
        {:else}
            <div class="cover placeholder">
                {(apt.title || '?').slice(0, 2).toUpperCase()}
            </div>
        {/if}
        <div class="cover-chip">
            <Chip tone={currentGuest ? 'ok' : apt.needs_cleaning ? 'due' : 'draft'}>
                {currentGuest ? `Занята до ${fmtDate(currentGuest.booking.check_out)}` : apt.needs_cleaning ? 'Требует уборки' : 'Свободна'}
            </Chip>
        </div>
    </div>

    <!-- KPI -->
    {#if stats}
        <div class="kpis">
            {#each [
                ['Ночей', stats.nights, fmtMonth(currentMonth)],
                ['ADR', fmtShortRub(stats.adr), ''],
                ['Выручка', fmtShortRub(stats.revenue), Math.round((stats.utilization || 0) * 100) + '%']
            ] as [lbl, val, meta]}
                <div class="kpi">
                    <div class="kpi-lbl">{lbl}</div>
                    <div class="kpi-val">{val}</div>
                    {#if meta}<div class="kpi-meta">{meta}</div>{/if}
                </div>
            {/each}
        </div>
    {/if}

    <!-- Current guest -->
    {#if currentGuest}
        <Section title="Гость">
            <div class="wrap">
                <Card pad={14}>
                    <button class="guest" type="button" onclick={() => currentGuest.client && goto(`/clients/${currentGuest.client.id}`)}>
                        <Avatar name={currentGuest.client?.full_name || '?'} size={44} accent="var(--accent)" />
                        <div class="guest-body">
                            <div class="guest-name">{currentGuest.client?.full_name || '—'}</div>
                            <div class="guest-phone">{currentGuest.client?.phone || ''}</div>
                        </div>
                    </button>
                    <div class="guest-range">
                        <span>{fmtDate(currentGuest.booking.check_in)} → {fmtDate(currentGuest.booking.check_out)}</span>
                        <span class="guest-sum">{fmtNights(currentGuest.booking.check_in, currentGuest.booking.check_out)} · {fmtRub(currentGuest.booking.total_price)}</span>
                    </div>
                </Card>
            </div>
        </Section>
    {/if}

    <!-- Характеристики -->
    <Section title="Характеристики">
        <div class="wrap">
            <Card pad={0}>
                {#each [
                    ['Тип', apt.rooms || '—'],
                    ['Площадь', apt.area_m2 ? apt.area_m2 + ' м²' : '—'],
                    ['Этаж', apt.floor || '—'],
                    ['Район', apt.district || '—'],
                    ['Цена/ночь', fmtRub(apt.price_per_night)],
                    ['Нужна уборка', apt.needs_cleaning ? 'Да' : 'Нет']
                ] as [k, v], i, arr}
                    <div class="ch-row" class:last={i === 5}>
                        <span class="ch-key">{k}</span>
                        <span class="ch-val">{v}</span>
                    </div>
                {/each}
            </Card>
        </div>
    </Section>

    <!-- Actions -->
    <div class="actions">
        {#if apt.needs_cleaning}
            <button class="primary" type="button" onclick={markClean}>Закрыть уборку ✓</button>
        {:else}
            <button class="ghost" type="button" onclick={markDirty}>Пометить грязной</button>
        {/if}
    </div>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .wrap { padding: 0 20px 14px; }
    .cover-wrap {
        margin: 0 20px 16px;
        height: 170px;
        border-radius: 10px;
        overflow: hidden;
        position: relative;
        background: var(--bg-subtle);
    }
    .cover {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .cover.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 34px;
        font-weight: 700;
        color: var(--faint);
    }
    .cover-chip {
        position: absolute;
        top: 12px;
        left: 12px;
    }

    .kpis {
        padding: 0 20px 14px;
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--card);
        margin: 0 20px 16px;
        overflow: hidden;
    }
    .kpi {
        padding: 12px 10px;
        text-align: center;
        border-right: 1px solid var(--border);
    }
    .kpi:last-child { border-right: none; }
    .kpi-lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--faint);
    }
    .kpi-val {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        margin-top: 4px;
        color: var(--ink);
    }
    .kpi-meta {
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        margin-top: 2px;
    }

    .guest {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        background: transparent;
        border: none;
        padding: 0 0 12px;
        cursor: pointer;
        text-align: left;
    }
    .guest-body { flex: 1; min-width: 0; }
    .guest-name { font-size: 15px; font-weight: 600; color: var(--ink); }
    .guest-phone { font-family: var(--font-mono); font-size: 11px; color: var(--faint); margin-top: 2px; }
    .guest-range {
        display: flex;
        justify-content: space-between;
        padding: 10px 12px;
        background: var(--bg-subtle);
        border-radius: 6px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
    }
    .guest-sum { color: var(--ink); font-weight: 600; }

    .ch-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-soft);
    }
    .ch-row.last { border-bottom: none; }
    .ch-key {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--faint);
        text-transform: uppercase;
    }
    .ch-val { font-size: 13px; color: var(--ink); font-weight: 500; }

    .actions {
        padding: 0 20px 24px;
        display: flex;
        gap: 10px;
    }
    .primary, .ghost {
        flex: 1;
        height: 46px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
