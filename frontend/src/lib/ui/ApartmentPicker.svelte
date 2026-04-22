<script>
    import { api } from '$lib/api.js';

    let { value, check_in, check_out, onChange } = $props();

    let query = $state('');
    let items = $state([]);
    let open = $state(false);
    let active = $state(0);
    let selected = $state(null);
    let loading = $state(false);
    let timer = null;

    async function fetchList(q) {
        loading = true;
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (check_in) params.set('check_in', check_in);
        if (check_out) params.set('check_out', check_out);
        try {
            items = await api.get(`/apartments?${params}`);
        } finally {
            loading = false;
        }
    }

    function debouncedFetch(q) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => fetchList(q), 200);
    }

    $effect(() => () => { if (timer) clearTimeout(timer); });

    $effect(() => {
        if (value && (!selected || selected.id !== value)) {
            api.get(`/apartments/${value}`).then(a => selected = a).catch(() => {});
        }
        if (!value) selected = null;
    });

    function focus() { open = true; if (items.length === 0) fetchList(''); }
    function pick(it) {
        selected = it;
        onChange(it.id);
        open = false;
        query = '';
    }

    function onKey(e) {
        if (!open) return;
        if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, items.length - 1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); }
        else if (e.key === 'Enter') { e.preventDefault(); if (items[active]) pick(items[active]); }
        else if (e.key === 'Escape') { open = false; }
    }

    function fmtTo(d) {
        if (!d) return null;
        const [_, m, day] = d.split('-');
        return `${day}.${m}`;
    }
</script>

<div class="picker">
    {#if selected && !open}
        <button type="button" class="selected" onclick={() => { open = true; query = ''; fetchList(''); }}>
            {#if selected.cover_url}
                <img class="thumb" src={selected.cover_url} alt="" />
            {:else}
                <div class="thumb placeholder"></div>
            {/if}
            <div class="meta">
                <div class="title">{selected.callsign || selected.title}</div>
                <div class="addr">{selected.address}</div>
            </div>
            <span class="change">Сменить</span>
        </button>
    {:else}
        <input
            type="text"
            placeholder="Поиск по позывному или адресу"
            bind:value={query}
            oninput={() => debouncedFetch(query)}
            onfocus={focus}
            onkeydown={onKey}
        />
        {#if open}
            <div class="dropdown">
                {#if loading}<div class="empty">…</div>{/if}
                {#each items as it, i}
                    <button
                        type="button"
                        class="row"
                        class:active={i === active}
                        onmouseenter={() => active = i}
                        onclick={() => pick(it)}
                    >
                        {#if it.cover_url}
                            <img class="thumb" src={it.cover_url} alt="" />
                        {:else}
                            <div class="thumb placeholder"></div>
                        {/if}
                        <div class="meta">
                            <div class="title">{it.callsign || it.title}</div>
                            <div class="addr">{it.address}</div>
                        </div>
                        {#if it.next_booked_from}
                            <span class="busy">до {fmtTo(it.next_booked_from)}</span>
                        {/if}
                    </button>
                {/each}
                {#if items.length === 0 && !loading}
                    <div class="empty">Ничего не найдено</div>
                {/if}
            </div>
        {/if}
    {/if}
</div>

<style>
    .picker { position: relative; }
    input {
        width: 100%; padding: 10px 12px;
        border: 1px solid var(--border); border-radius: 8px;
        font-size: 14px; background: var(--card); color: var(--ink);
    }
    .dropdown {
        position: absolute; top: calc(100% + 4px); left: 0; right: 0;
        max-height: 320px; overflow-y: auto; z-index: 30;
        background: var(--card); border: 1px solid var(--border); border-radius: 8px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    }
    .row, .selected {
        display: flex; align-items: center; gap: 10px;
        width: 100%; padding: 8px 10px;
        background: transparent; border: none; cursor: pointer; text-align: left;
        color: var(--ink);
    }
    .row.active { background: var(--card-hi, #f3f3f3); }
    .selected {
        border: 1px solid var(--border); border-radius: 8px;
        background: var(--card);
    }
    .thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; background: var(--card-hi, #eee); flex-shrink: 0; }
    .thumb.placeholder { background: var(--card-hi, #eee); }
    .meta { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .title { font-weight: 600; font-size: 13px; }
    .addr { font-size: 11px; color: var(--faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .busy { font-size: 11px; color: #c33; padding: 2px 6px; background: rgba(204,51,51,0.1); border-radius: 4px; flex-shrink: 0; }
    .change { font-size: 11px; color: var(--faint); margin-left: auto; flex-shrink: 0; }
    .empty { padding: 10px; color: var(--faint); font-size: 12px; }
</style>
