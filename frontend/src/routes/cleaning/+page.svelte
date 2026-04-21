<script>
    import { onMount } from 'svelte';
    import { api } from '$lib/api.js';
    import { goto } from '$app/navigation';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import { fmtRub } from '$lib/format.js';

    let apartments = $state([]);
    let error = $state(null);
    let loading = $state(true);

    async function load() {
        try {
            apartments = await api.get('/apartments/cleaning');
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function markClean(apt, e) {
        e.stopPropagation();
        try {
            await api.post(`/apartments/${apt.id}/mark-clean`);
            apartments = apartments.filter(a => a.id !== apt.id);
        } catch (err) {
            error = err.message;
        }
    }

    onMount(load);
</script>

<PageHead title="Уборка" sub="{apartments.length} в очереди" />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else if apartments.length === 0}
    <div class="empty">
        <Card pad={20}>
            <div class="empty-text">Все квартиры чистые ✓</div>
        </Card>
    </div>
{:else}
    <div class="list">
        {#each apartments as a}
            <button class="task" onclick={() => goto(`/apartments/${a.id}`)} type="button">
                <div class="top">
                    <div class="addr-wrap">
                        <div class="title">{a.title}</div>
                        <div class="addr">{a.address}</div>
                    </div>
                    <Chip tone="due">Требует уборки</Chip>
                </div>
                <div class="meta">
                    {a.rooms || '—'}
                    {#if a.area_m2} · {a.area_m2} м²{/if}
                    {#if a.district} · {a.district}{/if}
                    · {fmtRub(a.price_per_night)}/ноч
                </div>
                <div class="actions">
                    <button class="primary" onclick={(e) => markClean(a, e)} type="button">
                        Закрыть уборку ✓
                    </button>
                </div>
            </button>
        {/each}
    </div>
{/if}

<style>
    .loading, .empty { padding: 40px 20px; color: var(--faint); text-align: center; }
    .empty-text { text-align: center; color: var(--positive); font-weight: 600; }
    .list { padding: 0 20px 20px; display: flex; flex-direction: column; gap: 10px; }
    .task {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px;
        cursor: pointer;
        text-align: left;
        width: 100%;
    }
    .task:hover { background: var(--card-hi); }
    .top {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        align-items: flex-start;
        margin-bottom: 8px;
    }
    .addr-wrap { flex: 1; min-width: 0; }
    .title {
        font-size: 15px;
        font-weight: 600;
        color: var(--ink);
    }
    .addr {
        font-size: 12px;
        color: var(--muted);
        margin-top: 2px;
    }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 12px;
    }
    .actions { display: flex; justify-content: flex-end; }
    .primary {
        padding: 10px 14px;
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary:hover { background: var(--accent2); }
</style>
