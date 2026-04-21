<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';

    let apartments = $state([]);
    let calendar = $state([]);
    let error = $state(null);
    let loading = $state(true);

    const today = new Date();
    const from = today.toISOString().slice(0, 10);
    const toDate = new Date(today);
    toDate.setDate(toDate.getDate() + 14);
    const to = toDate.toISOString().slice(0, 10);

    const days = Array.from({ length: 14 }, (_, i) => {
        const d = new Date(today);
        d.setDate(d.getDate() + i);
        return d;
    });

    onMount(async () => {
        try {
            const [apts, cal] = await Promise.all([
                api.get('/apartments'),
                api.get(`/bookings/calendar?from=${from}&to=${to}`)
            ]);
            apartments = apts;
            calendar = cal;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    const todayISO = from;
    const COL_W = 24;
    const ROW_H = 36;

    function bookingsFor(aptId) {
        const entry = calendar.find(c => c.apartment_id === aptId);
        return entry ? entry.bookings : [];
    }

    // position: days from `from` date
    function startCol(b) {
        const ci = new Date(b.check_in);
        const start = new Date(from);
        return Math.max(0, Math.round((ci - start) / 86400000));
    }
    function widthCols(b) {
        const ci = new Date(Math.max(new Date(b.check_in), new Date(from)));
        const co = new Date(Math.min(new Date(b.check_out), new Date(to)));
        return Math.max(1, Math.round((co - ci) / 86400000));
    }
    function tone(b) {
        if (b.status === 'completed') return 'var(--positive)';
        return 'var(--accent)';
    }
</script>

<PageHead title="Шахматка" sub="{apartments.length} кв · 14 дней"
    back="Настройки" backOnClick={() => goto('/settings')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else}
    <div class="grid-wrap">
        <div class="grid" style:--col-w="{COL_W}px" style:--row-h="{ROW_H}px">
            <!-- header -->
            <div class="header-row">
                <div class="name-col">Апрель</div>
                {#each days as d, i}
                    {@const dt = d.toISOString().slice(0, 10)}
                    {@const isToday = dt === todayISO}
                    {@const weekend = d.getDay() === 0 || d.getDay() === 6}
                    <div class="day-cell" class:today={isToday} class:weekend>
                        {d.getDate()}
                    </div>
                {/each}
            </div>
            <!-- rows -->
            {#each apartments as a, ai}
                <div class="row">
                    <div class="name-col">{a.title}</div>
                    {#each days as d, i}
                        {@const dt = d.toISOString().slice(0, 10)}
                        <div class="cell" class:today={dt === todayISO}></div>
                    {/each}
                    {#each bookingsFor(a.id) as b}
                        <div
                            class="bar"
                            style:left="calc(110px + {startCol(b)} * var(--col-w) + 2px)"
                            style:width="calc({widthCols(b)} * var(--col-w) - 4px)"
                            style:background={tone(b)}
                            title={`${b.client_name} · ${b.check_in} → ${b.check_out}`}
                            onclick={() => goto(`/bookings/${b.id}`)}
                            role="button"
                            tabindex="0"
                            onkeydown={(e) => { if (e.key === 'Enter') goto(`/bookings/${b.id}`); }}
                        >
                            <span class="bar-text">{b.client_name.split(' ')[0]}</span>
                        </div>
                    {/each}
                </div>
            {/each}
        </div>

        <div class="legend">
            <span class="leg-item"><span class="leg-dot" style:background="var(--accent)"></span>активная</span>
            <span class="leg-item"><span class="leg-dot" style:background="var(--positive)"></span>закрыта</span>
        </div>
    </div>
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .grid-wrap {
        padding: 0 20px 24px;
        overflow-x: auto;
    }
    .grid {
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
        background: var(--card);
        min-width: calc(110px + 14 * var(--col-w));
    }
    .header-row, .row {
        display: grid;
        grid-template-columns: 110px repeat(14, var(--col-w));
        border-bottom: 1px solid var(--border-soft);
    }
    .row {
        height: var(--row-h);
        position: relative;
    }
    .row:last-child { border-bottom: none; }
    .header-row {
        background: var(--card-hi);
    }
    .name-col {
        padding: 8px 10px;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        border-right: 1px solid var(--border-soft);
        display: flex;
        align-items: center;
    }
    .row .name-col {
        font-family: var(--font-sans);
        font-size: 11px;
        color: var(--ink);
        font-weight: 500;
        text-transform: none;
        letter-spacing: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .day-cell, .cell {
        border-left: 1px solid var(--border-soft);
    }
    .day-cell {
        padding: 6px 0;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .day-cell.weekend { color: var(--muted); }
    .day-cell.today, .cell.today {
        background: var(--accent-bg);
        color: var(--accent);
        font-weight: 700;
    }
    .bar {
        position: absolute;
        top: 7px;
        height: calc(var(--row-h) - 14px);
        border-radius: 3px;
        opacity: 0.88;
        cursor: pointer;
        display: flex;
        align-items: center;
        padding: 0 4px;
        overflow: hidden;
    }
    .bar:hover { opacity: 1; }
    .bar-text {
        font-size: 9px;
        color: #fff;
        font-weight: 600;
        white-space: nowrap;
    }
    .legend {
        margin-top: 12px;
        display: flex;
        gap: 14px;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .leg-item { display: inline-flex; align-items: center; gap: 5px; }
    .leg-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
</style>
