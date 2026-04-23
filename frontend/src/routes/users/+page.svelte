<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import AddBtn from '$lib/ui/AddBtn.svelte';
    import { fmtRole } from '$lib/format.js';

    let users = $state([]);
    let me = $state(null);
    let error = $state(null);
    let loading = $state(true);

    onMount(async () => {
        me = getUser();
        if (!me || me.role !== 'owner') {
            error = 'Доступно только владельцу';
            loading = false;
            return;
        }
        try {
            users = await api.get('/users');
        } catch (e) {
            if (e instanceof ApiError && e.status === 403) {
                error = 'Нет прав';
            } else {
                error = e.message;
            }
        } finally {
            loading = false;
        }
    });

    const byRole = $derived({
        owner: users.filter(u => u.role === 'owner'),
        admin: users.filter(u => u.role === 'admin'),
        maid:  users.filter(u => u.role === 'maid')
    });
</script>

<PageHead title="Команда" sub="{users.length} пользователей"
    back="Настройки" backOnClick={() => goto('/settings')} />

{#if me?.role === 'owner'}
    <div class="add-row">
        <AddBtn onclick={() => goto('/users/new')} title="Добавить пользователя" />
    </div>
{/if}

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading}
    <div class="loading">Загрузка…</div>
{:else}
    <Section title="Пользователи">
        <div class="wrap">
            <Card pad={0}>
                {#each users as u, i}
                    <div class="row" class:last={i === users.length - 1}>
                        <Avatar name={u.full_name} size={38} role={u.role} accent={u.role === 'owner' ? 'var(--ink)' : null} />
                        <div class="body">
                            <div class="name">
                                {u.full_name}
                                {#if me && u.id === me.id}<span class="you">ВЫ</span>{/if}
                            </div>
                            <div class="meta">{fmtRole(u.role).toUpperCase()} · #{u.id}</div>
                        </div>
                    </div>
                {/each}
            </Card>
        </div>
    </Section>

    <Section title="Роли">
        <div class="wrap">
            <Card pad={0}>
                {#each [
                    ['Владелец', 'полный доступ', byRole.owner.length],
                    ['Администратор', 'брони, клиенты, квартиры', byRole.admin.length],
                    ['Горничная', 'только уборка', byRole.maid.length]
                ] as [n, d, c], i}
                    <div class="role-row" class:last={i === 2}>
                        <div>
                            <div class="role-name">{n}</div>
                            <div class="role-meta">{d.toUpperCase()} · {c}</div>
                        </div>
                    </div>
                {/each}
            </Card>
        </div>
    </Section>
{/if}

<style>
    .add-row { padding: 12px 20px 4px; display: flex; justify-content: flex-end; }
    .wrap { padding: 0 20px 14px; }
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .row {
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--border-soft);
    }
    .row.last { border-bottom: none; }
    .body { flex: 1; min-width: 0; }
    .name {
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .you {
        font-family: var(--font-mono);
        font-size: 9px;
        background: var(--ink);
        color: var(--bg);
        padding: 1px 5px;
        border-radius: 2px;
        letter-spacing: 0.5px;
    }
    .meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }
    .role-row {
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-soft);
    }
    .role-row.last { border-bottom: none; }
    .role-name { font-size: 14px; font-weight: 600; color: var(--ink); }
    .role-meta {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        margin-top: 2px;
    }
</style>
