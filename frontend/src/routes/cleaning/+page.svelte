<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let error = $state('');

    async function load() {
        try { items = await api.get('/apartments/cleaning'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    async function markClean(a) {
        try { await api.post(`/apartments/${a.id}/mark-clean`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка'; }
    }
</script>

<h1>Уборка</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

{#if items.length === 0}
    <div class="card" style="text-align:center">Всё чисто 🎉</div>
{:else}
    <div class="stack">
        {#each items as a}
            <div class="card">
                <div class="row">
                    <div style="flex:1">
                        <strong>{a.title}</strong><br/>
                        <span style="color:var(--muted)">{a.address}</span>
                    </div>
                    <button class="primary" onclick={() => markClean(a)}>Отметить убрано</button>
                </div>
            </div>
        {/each}
    </div>
{/if}
