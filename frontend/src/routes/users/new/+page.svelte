<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';

    let me = $state(null);
    let username = $state('');
    let password = $state('');
    let showPass = $state(false);
    let fullName = $state('');
    let role = $state('admin');
    let saving = $state(false);
    let error = $state(null);

    onMount(() => {
        me = getUser();
        if (!me || me.role !== 'owner') {
            error = 'Доступно только владельцу';
        }
    });

    async function submit() {
        error = null;
        if (!username.trim() || password.length < 8 || !fullName.trim()) {
            error = 'Заполни все поля; пароль >= 8 символов'; return;
        }
        saving = true;
        try {
            await api.post('/users', {
                username: username.trim(), password, full_name: fullName.trim(), role,
            });
            goto('/users');
        } catch (e) {
            error = e instanceof ApiError ? e.message : 'Ошибка';
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новый пользователь" back="Команда" backOnClick={() => goto('/users')} />

{#if error && error === 'Доступно только владельцу'}
    <div class="error-banner">{error}</div>
{:else}
    <Section title="Учётные данные">
        <div class="wrap">
            <Card pad={14}>
                <form onsubmit={(e) => { e.preventDefault(); submit(); }}>
                    <label>Username
                        <input type="text" bind:value={username} autocomplete="off" />
                    </label>
                    <label>Пароль
                        <div class="pass">
                            <input type={showPass ? 'text' : 'password'} bind:value={password} />
                            <button type="button" onclick={() => showPass = !showPass}>
                                {showPass ? 'Скрыть' : 'Показать'}
                            </button>
                        </div>
                    </label>
                    <label>Полное имя
                        <input type="text" bind:value={fullName} />
                    </label>
                    <label>Роль
                        <select bind:value={role}>
                            <option value="owner">Владелец</option>
                            <option value="admin">Админ</option>
                            <option value="maid">Горничная</option>
                        </select>
                    </label>
                    {#if error && error !== 'Доступно только владельцу'}
                        <div class="err">{error}</div>
                    {/if}
                    <button type="submit" class="primary" disabled={saving}>
                        {saving ? 'Создание...' : 'Создать'}
                    </button>
                </form>
            </Card>
        </div>
    </Section>
{/if}

<style>
    .wrap { padding: 0 16px; }
    form { display: flex; flex-direction: column; gap: 12px; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--faint); }
    input, select { padding: 6px 8px; font-size: 14px; border: 1px solid var(--border); border-radius: 6px; }
    .pass { display: flex; gap: 6px; }
    .pass input { flex: 1; }
    .pass button { font-size: 11px; padding: 0 8px; background: transparent; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; }
    .primary:disabled { opacity: 0.5; }
    .err { font-size: 12px; color: #c33; }
    .error-banner { padding: 12px; color: #c33; }
</style>
