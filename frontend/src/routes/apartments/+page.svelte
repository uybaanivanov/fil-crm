<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let editingId = $state(null);
    let form = $state({ title: '', address: '', price_per_night: 0 });

    async function load() {
        try { items = await api.get('/apartments'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        editingId = null;
        form = { title: '', address: '', price_per_night: 0 };
        showForm = true; error = '';
    }
    function openEdit(a) {
        editingId = a.id;
        form = { title: a.title, address: a.address, price_per_night: a.price_per_night };
        showForm = true; error = '';
    }
    async function save() {
        try {
            if (editingId === null) await api.post('/apartments', form);
            else await api.patch(`/apartments/${editingId}`, form);
            showForm = false;
            await load();
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(a) {
        if (!confirm(`Удалить квартиру «${a.title}»?`)) return;
        try { await api.delete(`/apartments/${a.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }
    async function markDirty(a) {
        try { await api.post(`/apartments/${a.id}/mark-dirty`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка'; }
    }
    async function markClean(a) {
        try { await api.post(`/apartments/${a.id}/mark-clean`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка'; }
    }
</script>

<h1>Квартиры</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новая квартира</button>
</div>

{#if showForm}
    <div class="card">
        <h2>{editingId === null ? 'Новая квартира' : `Редактировать #${editingId}`}</h2>
        <div class="grid-form">
            <label>Название</label>    <input bind:value={form.title} />
            <label>Адрес</label>       <input bind:value={form.address} />
            <label>Цена за ночь, ₽</label><input type="number" min="1" bind:value={form.price_per_night} />
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead>
        <tr><th>Название</th><th>Адрес</th><th>₽/ночь</th><th>Статус</th><th></th></tr>
    </thead>
    <tbody>
        {#each items as a}
            <tr>
                <td>{a.title}</td>
                <td>{a.address}</td>
                <td>{a.price_per_night.toLocaleString('ru-RU')}</td>
                <td>
                    {#if a.needs_cleaning}
                        <span class="badge warn">требует уборки</span>
                    {:else}
                        <span class="badge ok">чисто</span>
                    {/if}
                </td>
                <td>
                    <div class="row" style="justify-content:flex-end">
                        {#if a.needs_cleaning}
                            <button onclick={() => markClean(a)}>Отметить убрано</button>
                        {:else}
                            <button onclick={() => markDirty(a)}>Пометить грязно</button>
                        {/if}
                        <button onclick={() => openEdit(a)}>Редактировать</button>
                        <button class="danger" onclick={() => remove(a)}>Удалить</button>
                    </div>
                </td>
            </tr>
        {/each}
        {#if items.length === 0}
            <tr><td colspan="5" style="text-align:center; color:var(--muted)">Пока нет квартир</td></tr>
        {/if}
    </tbody>
</table>
