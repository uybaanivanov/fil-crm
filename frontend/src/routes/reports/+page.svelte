<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import { fmtShortRub, fmtRub } from '$lib/format.js';
    import HelpTip from '$lib/ui/HelpTip.svelte';

    let period = $state('month');
    let data = $state(null);
    let error = $state(null);
    let loading = $state(true);

    async function load(p) {
        loading = true;
        try {
            data = await api.get(`/reports?period=${p}`);
            period = p;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(() => load('month'));

    const periods = [
        ['week', 'Неделя'],
        ['month', 'Месяц'],
        ['quarter', 'Квартал'],
        ['year', 'Год']
    ];
</script>

<PageHead title="Отчёты" sub={period} back="Настройки" backOnClick={() => goto('/settings')} />

<div class="tabs">
    {#each periods as [val, lbl]}
        <button class="tab" class:active={period === val} type="button" onclick={() => load(val)}>
            {lbl}
        </button>
    {/each}
</div>

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !data}
    <div class="loading">Загрузка…</div>
{:else}
    <div class="kpis">
        {#each [
            { lbl: 'Занятость', val: Math.round((data.occupancy || 0) * 1000) / 10 + '%', term: null },
            { lbl: 'ADR', val: fmtShortRub(data.adr), term: 'adr' },
            { lbl: 'RevPAR', val: fmtShortRub(data.revpar), term: 'revpar' },
            { lbl: 'Ср. ночи', val: (data.avg_nights || 0).toFixed(1), term: null }
        ] as k}
            <Card pad={14}>
                <div class="eyebrow">
                    {k.lbl}
                    {#if k.term}<HelpTip term={k.term}/>{/if}
                </div>
                <div class="val">{k.val}</div>
            </Card>
        {/each}
    </div>

    <Section title="Загрузка по квартирам">
        <div class="wrap">
            <Card pad={14}>
                {#if data.per_apartment.length === 0}
                    <div class="empty">Нет данных за период</div>
                {:else}
                    {#each data.per_apartment as a, i}
                        {@const pct = Math.round((a.util || 0) * 100)}
                        {@const color = pct > 80 ? 'var(--positive)' : pct > 65 ? 'var(--caution)' : 'var(--muted)'}
                        <div class="bar-row" class:last={i === data.per_apartment.length - 1}>
                            <span class="bar-name" title={a.title}>
                                {#if a.callsign}<span class="cs">{a.callsign}</span>{:else}{a.title}{/if}
                            </span>
                            <div class="bar">
                                <div class="bar-fill" style:width="{pct}%" style:background={color}></div>
                            </div>
                            <span class="bar-pct">{pct}%</span>
                        </div>
                    {/each}
                {/if}
            </Card>
        </div>
    </Section>

    <div class="foot">
        <span class="eyebrow">ПЕРИОД</span>
        <span class="range">{data.from} → {data.to}</span>
    </div>
{/if}

<style>
    .tabs {
        padding: 0 20px 14px;
        display: flex;
        gap: 6px;
    }
    .tab {
        flex: 1;
        height: 32px;
        border-radius: 6px;
        background: var(--card);
        border: 1px solid var(--border);
        color: var(--ink2);
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
    }
    .tab.active {
        background: var(--ink);
        color: var(--bg);
        border-color: var(--ink);
    }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty { color: var(--faint); text-align: center; padding: 12px; }
    .kpis {
        padding: 0 20px 14px;
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
        font-weight: 500;
    }
    .val {
        font-family: var(--font-serif);
        font-size: 26px;
        line-height: 1;
        color: var(--ink);
        margin-top: 8px;
    }
    .wrap { padding: 0 20px 14px; }
    .bar-row {
        display: grid;
        grid-template-columns: 120px 1fr 44px;
        gap: 10px;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .bar-row.last { border-bottom: none; }
    .bar-name {
        font-size: 11px;
        color: var(--ink);
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .bar {
        height: 6px;
        background: var(--border-soft);
        border-radius: 3px;
        overflow: hidden;
    }
    .bar-fill { height: 100%; }
    .cs { font-family: var(--font-mono); color: var(--accent); font-weight: 600; }
    .bar-pct {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
        text-align: right;
    }
    .foot {
        padding: 0 20px 24px;
        display: flex;
        gap: 10px;
        align-items: center;
    }
    .range {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--ink2);
    }
</style>
