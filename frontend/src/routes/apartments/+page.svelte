<script>
    import { onMount } from 'svelte';
    import { api } from '$lib/api.js';
    import { goto } from '$app/navigation';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Searchbar from '$lib/ui/Searchbar.svelte';
    import FilterChips from '$lib/ui/FilterChips.svelte';
    import AddBtn from '$lib/ui/AddBtn.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import { getUser } from '$lib/auth.js';

    const me = getUser();
    const canAdd = me?.role === 'owner';

    let apartments = $state([]);
    let error = $state(null);
    let loading = $state(true);
    let query = $state('');
    let filter = $state('all');

    const currentMonth = new Date().toISOString().slice(0, 7);

    onMount(async () => {
        try {
            apartments = await api.get(`/apartments?with_stats=1&month=${currentMonth}`);
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    const counts = $derived({
        all: apartments.length,
        occupied: apartments.filter(a => a.status === 'occupied').length,
        free: apartments.filter(a => a.status === 'free').length,
        needs_cleaning: apartments.filter(a => a.status === 'needs_cleaning').length
    });

    const filterItems = $derived([
        { label: 'Все',       value: 'all',            count: counts.all,            active: filter === 'all' },
        { label: 'Занято',    value: 'occupied',       count: counts.occupied,       active: filter === 'occupied' },
        { label: 'Свободно',  value: 'free',           count: counts.free,           active: filter === 'free' },
        { label: 'Уборка',    value: 'needs_cleaning', count: counts.needs_cleaning, active: filter === 'needs_cleaning' }
    ]);

    const visible = $derived(
        apartments
            .filter(a => filter === 'all' || a.status === filter)
            .filter(a => {
                if (!query) return true;
                const q = query.toLowerCase();
                return (a.title || '').toLowerCase().includes(q)
                    || (a.address || '').toLowerCase().includes(q);
            })
    );

    function statusChip(a) {
        if (a.status === 'occupied') return { tone: 'ok', label: 'Занята' };
        if (a.status === 'needs_cleaning') return { tone: 'due', label: 'Уборка' };
        return { tone: 'draft', label: 'Свободна' };
    }

    function metaLine(a) {
        const parts = [];
        if (a.rooms) parts.push(a.rooms);
        if (a.area_m2) parts.push(`${a.area_m2} м²`);
        if (a.district) parts.push(a.district);
        return parts.join(' · ') || '—';
    }
</script>

<PageHead title="Квартиры" sub="{apartments.length} объектов · {counts.occupied} занято">
    {#snippet right()}
        {#if canAdd}
            <AddBtn onclick={() => goto('/apartments/new')} />
        {/if}
    {/snippet}
</PageHead>

<div class="search-row">
    <div class="search"><Searchbar bind:value={query} placeholder="Адрес, название…" /></div>
</div>

<FilterChips items={filterItems} onselect={(v) => (filter = v)} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else if visible.length === 0}
    <div class="empty">Ничего не найдено</div>
{:else}
    <div class="list">
        {#each visible as a}
            <button class="apt" onclick={() => goto(`/apartments/${a.id}`)} type="button">
                {#if a.cover_url}
                    <img src={a.cover_url} alt="" class="cover" />
                {:else}
                    <div class="cover placeholder">{(a.title || a.address || '?').slice(0, 2).toUpperCase()}</div>
                {/if}
                <div class="apt-body">
                    <div class="apt-head">
                        <div class="title">{a.title}</div>
                        {#each [statusChip(a)] as s}
                            <Chip tone={s.tone}>{s.label}</Chip>
                        {/each}
                    </div>
                    <div class="addr">{a.address}</div>
                    <div class="meta">{metaLine(a)}</div>
                    <div class="util-row">
                        <div class="bar">
                            <div class="bar-fill" style:width="{Math.round((a.utilization || 0) * 100)}%"></div>
                        </div>
                        <span class="util-num">{Math.round((a.utilization || 0) * 100)}%</span>
                    </div>
                </div>
            </button>
        {/each}
    </div>
{/if}

<style>
    .search-row { padding: 0 20px 14px; }
    .loading, .empty { padding: 40px 20px; color: var(--faint); text-align: center; }
    .list { padding: 0 20px 20px; display: flex; flex-direction: column; gap: 10px; }
    .apt {
        display: flex;
        gap: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px;
        text-align: left;
        cursor: pointer;
        width: 100%;
    }
    .apt:hover { background: var(--card-hi); }
    .cover {
        width: 64px;
        height: 64px;
        border-radius: 6px;
        object-fit: cover;
        flex-shrink: 0;
        background: var(--bg-subtle);
    }
    .cover.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 14px;
        color: var(--faint);
        font-weight: 600;
    }
    .apt-body { flex: 1; min-width: 0; }
    .apt-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 4px;
    }
    .title {
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .addr {
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 4px;
    }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 10px;
    }
    .util-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .bar {
        flex: 1;
        height: 3px;
        background: var(--border-soft);
        border-radius: 2px;
        overflow: hidden;
    }
    .bar-fill { height: 100%; background: var(--accent); }
    .util-num {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--muted);
        min-width: 32px;
        text-align: right;
    }
</style>
