<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { setUser } from '$lib/auth.js';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRole } from '$lib/format.js';
    import { DEMO } from '$lib/demo.js';

    let users = $state([]);
    let loading = $state(true);
    let error = $state(null);

    onMount(async () => {
        try {
            users = await api.get('/dev_auth/users', { auth: false });
        } catch (e) {
            if (e instanceof ApiError && e.status === 404) {
                error = 'Dev-picker отключён. Запусти backend с DEBUG=1.';
            } else {
                error = e.message || 'Ошибка загрузки';
            }
        } finally {
            loading = false;
        }
    });

    async function pick(u) {
        try {
            const profile = await api.post('/dev_auth/login', { user_id: u.id }, { auth: false });
            setUser(profile);
            goto(profile.role === 'maid' ? '/cleaning' : '/');
        } catch (e) {
            error = e.message || 'Не удалось войти';
        }
    }
</script>

<div class="page">
    <header class="head">
        {#if !DEMO}
            <button class="back" onclick={() => goto('/login')} type="button">← Назад</button>
        {/if}
        <h1 class="title">{DEMO ? 'Демо' : 'Dev picker'}</h1>
        <div class="sub">
            {#if DEMO}
                Выбери роль чтобы войти. Изменения видны только тебе и не сохраняются после ресета базы.
            {:else}
                Вход без пароля — только локально
            {/if}
        </div>
    </header>

    {#if loading}
        <div class="state">Загрузка…</div>
    {:else if error}
        <div class="state error">{error}</div>
    {:else if users.length === 0}
        <div class="state">В базе нет пользователей. Создай через sqlite или POST /users.</div>
    {:else}
        <ul class="list">
            {#each users as u}
                <li>
                    <button onclick={() => pick(u)} class="user" type="button">
                        <Avatar name={u.full_name} size={40} role={u.role} accent="var(--ink)" />
                        <div class="body">
                            <div class="name">{u.full_name}</div>
                            <div class="role">{fmtRole(u.role)}</div>
                        </div>
                        <div class="id">#{u.id}</div>
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .page { padding: 28px 20px 40px; }
    .head { margin-bottom: 20px; }
    .back {
        background: transparent;
        border: none;
        color: var(--accent);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        padding: 0 0 12px;
    }
    .title {
        font-family: var(--font-serif);
        font-size: 28px;
        margin: 0;
        font-weight: 400;
        color: var(--ink);
    }
    .sub {
        font-family: var(--font-mono);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--faint);
        margin-top: 4px;
    }
    .state { padding: 20px 0; color: var(--muted); }
    .state.error { color: var(--danger); }
    .list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .user {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        cursor: pointer;
        text-align: left;
    }
    .user:hover { background: var(--card-hi); }
    .body { flex: 1; }
    .name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .role {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        margin-top: 2px;
    }
    .id {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--faint);
    }
</style>
