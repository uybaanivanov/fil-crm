<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let editingId = $state(null);
    let form = $state({ full_name: '', phone: '', source: '', notes: '' });

    async function load() {
        try { items = await api.get('/clients'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        editingId = null;
        form = { full_name: '', phone: '', source: '', notes: '' };
        showForm = true; error = '';
    }
    function openEdit(c) {
        editingId = c.id;
        form = { full_name: c.full_name, phone: c.phone, source: c.source || '', notes: c.notes || '' };
        showForm = true; error = '';
    }
    async function save() {
        const payload = { ...form };
        if (!payload.source) delete payload.source;
        if (!payload.notes)  delete payload.notes;
        try {
            if (editingId === null) await api.post('/clients', payload);
            else await api.patch(`/clients/${editingId}`, payload);
            showForm = false;
            await load();
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(c) {
        if (!confirm(`Удалить клиента «${c.full_name}»?`)) return;
        try { await api.delete(`/clients/${c.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }
</script>

<h1>Клиенты</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новый клиент</button>
</div>

{#if showForm}
    <div class="card">
        <h2>{editingId === null ? 'Новый клиент' : `Редактировать #${editingId}`}</h2>
        <div class="grid-form">
            <label>ФИО</label>      <input bind:value={form.full_name} />
            <label>Телефон</label>  <input bind:value={form.phone} />
            <label>Источник</label>
            <select bind:value={form.source}>
                <option value="">—</option>
                <option value="avito">Avito</option>
                <option value="booking">Booking</option>
                <option value="прямой">Прямой</option>
                <option value="другое">Другое</option>
            </select>
            <label>Заметки</label>  <textarea rows="3" bind:value={form.notes}></textarea>
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead><tr><th>ФИО</th><th>Телефон</th><th>Источник</th><th>Заметки</th><th></th></tr></thead>
    <tbody>
        {#each items as c}
            <tr>
                <td>{c.full_name}</td>
                <td>{c.phone}</td>
                <td>{c.source || '—'}</td>
                <td style="max-width:320px; color:var(--muted)">{c.notes || ''}</td>
                <td>
                    <div class="row" style="justify-content:flex-end">
                        <button onclick={() => openEdit(c)}>Редактировать</button>
                        <button class="danger" onclick={() => remove(c)}>Удалить</button>
                    </div>
                </td>
            </tr>
        {/each}
        {#if items.length === 0}
            <tr><td colspan="5" style="text-align:center; color:var(--muted)">Пока нет клиентов</td></tr>
        {/if}
    </tbody>
</table>
