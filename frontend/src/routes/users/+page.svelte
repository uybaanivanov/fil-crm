<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';

    let items = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let form = $state({ full_name: '', role: 'admin' });
    const me = getUser();

    async function load() {
        try { items = await api.get('/users'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        form = { full_name: '', role: 'admin' };
        showForm = true; error = '';
    }
    async function save() {
        try { await api.post('/users', form); showForm = false; await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(u) {
        if (!confirm(`Удалить пользователя «${u.full_name}»?`)) return;
        try { await api.delete(`/users/${u.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }
</script>

<h1>Пользователи</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новый пользователь</button>
</div>

{#if showForm}
    <div class="card">
        <h2>Новый пользователь</h2>
        <div class="grid-form">
            <label>ФИО</label>  <input bind:value={form.full_name} />
            <label>Роль</label>
            <select bind:value={form.role}>
                <option value="owner">owner</option>
                <option value="admin">admin</option>
                <option value="maid">maid</option>
            </select>
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead><tr><th>ФИО</th><th>Роль</th><th></th></tr></thead>
    <tbody>
        {#each items as u}
            <tr>
                <td>{u.full_name}</td>
                <td><span class="badge">{u.role}</span></td>
                <td style="text-align:right">
                    {#if me && me.id !== u.id}
                        <button class="danger" onclick={() => remove(u)}>Удалить</button>
                    {:else}
                        <span class="badge">вы</span>
                    {/if}
                </td>
            </tr>
        {/each}
    </tbody>
</table>
