<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { setUser } from '$lib/auth.js';

    let users = $state([]);
    let error = $state('');

    onMount(async () => {
        try {
            users = await api.get('/auth/users', { auth: false });
        } catch (e) {
            error = e instanceof ApiError ? e.detail : 'Не удалось загрузить список пользователей';
        }
    });

    async function login(u) {
        try {
            const me = await api.post('/auth/login', { user_id: u.id }, { auth: false });
            setUser(me);
            goto(me.role === 'maid' ? '/cleaning' : '/apartments');
        } catch (e) {
            error = e instanceof ApiError ? e.detail : 'Ошибка входа';
        }
    }
</script>

<h1>Вход</h1>

{#if error}
    <div class="error-banner">{error}</div>
{/if}

<div class="stack">
    {#each users as u}
        <button class="card" onclick={() => login(u)}>
            <div class="row">
                <strong style="flex:1">{u.full_name}</strong>
                <span class="badge">{u.role}</span>
            </div>
        </button>
    {/each}
    {#if users.length === 0 && !error}
        <div class="card">Нет пользователей. Запусти seed-скрипт.</div>
    {/if}
</div>
