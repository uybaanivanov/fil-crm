<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtDate, fmtDateFull, fmtNights } from '$lib/format.js';

    const me = getUser();
    const canDelete = me?.role === 'owner';

    const bookingId = $derived(parseInt(page.params.id, 10));

    let booking = $state(null);
    let client = $state(null);
    let apt = $state(null);
    let visitsCount = $state(0);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        loading = true;
        try {
            booking = await api.get(`/bookings/${bookingId}`);
            const [c, a] = await Promise.all([
                api.get(`/clients/${booking.client_id}`),
                api.get(`/apartments/${booking.apartment_id}`)
            ]);
            client = c;
            apt = a;
            visitsCount = c.stats?.count || 0;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    async function complete() {
        if (!confirm('Зафиксировать бронь как закрытую?')) return;
        try {
            await api.patch(`/bookings/${bookingId}`, { status: 'completed' });
            await load();
        } catch (e) {
            error = e.message;
        }
    }

    async function cancel() {
        if (!confirm('Отменить бронь?')) return;
        try {
            await api.patch(`/bookings/${bookingId}`, { status: 'cancelled' });
            await load();
        } catch (e) {
            error = e.message;
        }
    }

    async function remove() {
        if (!confirm(`Удалить бронь #${bookingId} безвозвратно? Это действие нельзя отменить.`)) return;
        try {
            await api.delete(`/bookings/${bookingId}`);
            goto('/bookings');
        } catch (e) {
            error = e.message;
        }
    }

    function statusLabel(s) {
        return { active: 'активная', completed: 'закрыта', cancelled: 'отменена' }[s] || s;
    }
    function statusTone(s) {
        return { active: 'ok', completed: 'ok', cancelled: 'late' }[s] || 'info';
    }

    const nights = $derived(booking ? Math.round((new Date(booking.check_out) - new Date(booking.check_in)) / 86400000) : 0);
    const perNight = $derived(booking && nights ? Math.round(booking.total_price / nights) : 0);
</script>

<PageHead title={booking ? `Бронь #${booking.id}` : 'Бронь'}
    sub={booking ? (booking.source || 'Без источника') : ''}
    back="Брони" backOnClick={() => goto('/bookings')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !booking}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Основное -->
    <div class="wrap">
        <Card pad={14}>
            <div class="chip-row">
                <Chip tone={statusTone(booking.status)}>{statusLabel(booking.status)}</Chip>
                {#if booking.source}
                    <Chip tone="info">{booking.source}</Chip>
                {/if}
                <span class="nights">{fmtNights(booking.check_in, booking.check_out)}</span>
            </div>
            <div class="dates">
                <div class="date-block">
                    <div class="dt-lbl">Заезд</div>
                    <div class="dt-val">{fmtDate(booking.check_in)}<span class="dt-time">14:00</span></div>
                </div>
                <svg class="arrow" width="18" height="12" viewBox="0 0 18 12" fill="none">
                    <path d="M1 6h16m0 0l-4-4m4 4l-4 4" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" />
                </svg>
                <div class="date-block right">
                    <div class="dt-lbl">Выезд</div>
                    <div class="dt-val">{fmtDate(booking.check_out)}<span class="dt-time">12:00</span></div>
                </div>
            </div>
        </Card>
    </div>

    <!-- Apartment -->
    <Section title="Квартира">
        <div class="wrap">
            <button class="apt-card" onclick={() => goto(`/apartments/${booking.apartment_id}`)} type="button">
                {#if apt?.cover_url}
                    <img src={apt.cover_url} alt="" class="apt-thumb" />
                {:else}
                    <div class="apt-thumb placeholder">
                        {(apt?.title || '?').slice(0, 2).toUpperCase()}
                    </div>
                {/if}
                <div class="apt-info">
                    <div class="apt-t">{apt?.title || booking.apartment_title}</div>
                    <div class="apt-meta">
                        {apt?.rooms || ''}
                        {#if apt?.area_m2}· {apt.area_m2} м²{/if}
                        {#if apt?.district} · {apt.district}{/if}
                    </div>
                </div>
            </button>
        </div>
    </Section>

    <!-- Guest -->
    <Section title="Гость">
        <div class="wrap">
            <button class="guest-card" onclick={() => goto(`/clients/${booking.client_id}`)} type="button">
                <Avatar name={client?.full_name || '?'} size={40} accent="var(--accent)" />
                <div class="guest-info">
                    <div class="guest-name">{client?.full_name || booking.client_name}</div>
                    <div class="guest-phone">
                        {client?.phone || ''}
                        {#if visitsCount > 0} · {visitsCount}-й визит{/if}
                    </div>
                </div>
            </button>
        </div>
    </Section>

    <!-- Расчёт -->
    <Section title="Расчёт">
        <div class="wrap">
            <Card pad={0}>
                <div class="calc-row">
                    <span>{nights} ночи × {fmtRub(perNight)}</span>
                    <span class="calc-num">{fmtRub(booking.total_price)}</span>
                </div>
            </Card>
        </div>
    </Section>

    {#if booking.notes}
        <Section title="Заметка">
            <div class="wrap"><Card pad={14}><div class="note">{booking.notes}</div></Card></div>
        </Section>
    {/if}

    <!-- Actions -->
    <div class="actions">
        {#if booking.status === 'active'}
            <button class="ghost" type="button" onclick={cancel}>Отменить</button>
            <button class="primary" type="button" onclick={complete}>Закрыть бронь →</button>
        {:else}
            <div class="closed">{statusLabel(booking.status).toUpperCase()}</div>
        {/if}
    </div>

    {#if canDelete}
        <div class="danger-zone">
            <button class="danger" type="button" onclick={remove}>
                Удалить бронь безвозвратно
            </button>
        </div>
    {/if}
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .wrap { padding: 0 20px 14px; }
    .chip-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .nights {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .dates {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .date-block { flex: 1; }
    .date-block.right { text-align: right; }
    .dt-lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
    }
    .dt-val {
        font-family: var(--font-serif);
        font-size: 22px;
        color: var(--ink);
        margin-top: 4px;
    }
    .dt-time {
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 12px;
        margin-left: 6px;
    }
    .arrow { flex-shrink: 0; }

    .apt-card, .guest-card {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: left;
        cursor: pointer;
    }
    .apt-card:hover, .guest-card:hover { background: var(--card-hi); }
    .apt-thumb {
        width: 60px;
        height: 60px;
        border-radius: 6px;
        object-fit: cover;
        background: var(--bg-subtle);
    }
    .apt-thumb.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 14px;
        color: var(--faint);
        font-weight: 600;
    }
    .apt-info { flex: 1; min-width: 0; }
    .apt-t { font-size: 14px; font-weight: 600; color: var(--ink); }
    .apt-meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 3px;
        text-transform: uppercase;
    }

    .guest-info { flex: 1; min-width: 0; }
    .guest-name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .guest-phone {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }

    .calc-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 14px;
        font-size: 13px;
    }
    .calc-row span:first-child { color: var(--muted); }
    .calc-num {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
    }

    .note { font-size: 13px; color: var(--ink2); line-height: 1.5; }

    .actions {
        padding: 4px 20px 24px;
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 10px;
    }
    .primary, .ghost {
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
    .closed {
        grid-column: 1 / -1;
        padding: 14px;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
        letter-spacing: 0.08em;
        background: var(--bg-subtle);
        border-radius: 6px;
    }
    .danger-zone {
        padding: 0 20px 24px;
        margin-top: 8px;
        border-top: 1px solid var(--border-soft);
        padding-top: 16px;
    }
    .danger {
        width: 100%;
        height: 42px;
        background: transparent;
        color: var(--danger);
        border: 1px solid var(--danger);
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
    }
    .danger:hover {
        background: var(--danger-bg);
    }
</style>
