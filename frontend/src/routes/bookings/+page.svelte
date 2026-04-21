<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let apartments = $state([]);
    let clients = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let editingId = $state(null);
    let form = $state({
        apartment_id: '', client_id: '', check_in: '', check_out: '',
        total_price: 0, status: 'active', notes: ''
    });

    async function load() {
        try {
            [items, apartments, clients] = await Promise.all([
                api.get('/bookings'), api.get('/apartments'), api.get('/clients')
            ]);
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        editingId = null;
        form = { apartment_id: '', client_id: '', check_in: '', check_out: '',
                 total_price: 0, status: 'active', notes: '' };
        showForm = true; error = '';
    }
    function openEdit(b) {
        editingId = b.id;
        form = {
            apartment_id: b.apartment_id, client_id: b.client_id,
            check_in: b.check_in, check_out: b.check_out,
            total_price: b.total_price, status: b.status, notes: b.notes || ''
        };
        showForm = true; error = '';
    }
    async function save() {
        const payload = { ...form };
        payload.apartment_id = Number(payload.apartment_id);
        payload.client_id    = Number(payload.client_id);
        payload.total_price  = Number(payload.total_price);
        if (!payload.notes) delete payload.notes;
        try {
            if (editingId === null) {
                delete payload.status;
                await api.post('/bookings', payload);
            } else {
                await api.patch(`/bookings/${editingId}`, payload);
            }
            showForm = false;
            await load();
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(b) {
        if (!confirm(`Удалить бронь #${b.id}?`)) return;
        try { await api.delete(`/bookings/${b.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }

    const statusLabel = { active: 'активна', cancelled: 'отменена', completed: 'завершена' };
    const statusClass = { active: 'ok', cancelled: 'warn', completed: '' };
</script>

<h1>Брони</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новая бронь</button>
</div>

{#if showForm}
    <div class="card">
        <h2>{editingId === null ? 'Новая бронь' : `Редактировать #${editingId}`}</h2>
        <div class="grid-form">
            <label>Квартира</label>
            <select bind:value={form.apartment_id}>
                <option value="">—</option>
                {#each apartments as a}<option value={a.id}>{a.title}</option>{/each}
            </select>
            <label>Клиент</label>
            <select bind:value={form.client_id}>
                <option value="">—</option>
                {#each clients as c}<option value={c.id}>{c.full_name}</option>{/each}
            </select>
            <label>Заезд</label>    <input type="date" bind:value={form.check_in} />
            <label>Выезд</label>    <input type="date" bind:value={form.check_out} />
            <label>Сумма, ₽</label> <input type="number" min="1" bind:value={form.total_price} />
            {#if editingId !== null}
                <label>Статус</label>
                <select bind:value={form.status}>
                    <option value="active">активна</option>
                    <option value="cancelled">отменена</option>
                    <option value="completed">завершена</option>
                </select>
            {/if}
            <label>Заметки</label>  <textarea rows="3" bind:value={form.notes}></textarea>
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead>
        <tr><th>Квартира</th><th>Клиент</th><th>Заезд</th><th>Выезд</th><th>Сумма</th><th>Статус</th><th></th></tr>
    </thead>
    <tbody>
        {#each items as b}
            <tr>
                <td>{b.apartment_title}</td>
                <td>{b.client_name}</td>
                <td>{b.check_in}</td>
                <td>{b.check_out}</td>
                <td>{b.total_price.toLocaleString('ru-RU')} ₽</td>
                <td><span class="badge {statusClass[b.status] || ''}">{statusLabel[b.status] || b.status}</span></td>
                <td>
                    <div class="row" style="justify-content:flex-end">
                        <button onclick={() => openEdit(b)}>Редактировать</button>
                        <button class="danger" onclick={() => remove(b)}>Удалить</button>
                    </div>
                </td>
            </tr>
        {/each}
        {#if items.length === 0}
            <tr><td colspan="7" style="text-align:center; color:var(--muted)">Пока нет броней</td></tr>
        {/if}
    </tbody>
</table>
