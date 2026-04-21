<script>
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';

    let url = $state('');
    let title = $state('');
    let address = $state('');
    let rooms = $state('2-комн');
    let area = $state('');
    let floor = $state('');
    let district = $state('');
    let price = $state('');
    let coverUrl = $state('');
    let ownerPhone = $state('');
    let saving = $state(false);
    let error = $state(null);

    const ROOMS_OPTIONS = ['Студия', '1-комн', '2-комн', '3+'];

    async function save() {
        error = null;
        if (!title || !address || !price) {
            error = 'Заполни название, адрес и цену';
            return;
        }
        const priceNum = parseInt(price, 10);
        if (!priceNum || priceNum <= 0) {
            error = 'Цена должна быть > 0';
            return;
        }
        saving = true;
        try {
            const payload = {
                title,
                address,
                price_per_night: priceNum
            };
            if (rooms) payload.rooms = rooms;
            if (area) payload.area_m2 = parseInt(area, 10);
            if (floor) payload.floor = floor;
            if (district) payload.district = district;
            if (coverUrl) payload.cover_url = coverUrl;
            const result = await api.post('/apartments', payload);
            goto(`/apartments/${result.id}`);
        } catch (e) {
            error = e.message;
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новая квартира" sub="Заполни или вставь ссылку с площадки"
    back="Отмена" backOnClick={() => goto('/apartments')} />

<!-- URL paste (декоративно) -->
<div class="wrap">
    <div class="eyebrow">Ссылка на объявление</div>
    <input class="url-field" bind:value={url} placeholder="https://doska.ykt.ru/board/..." />
    <div class="hint">Поддерживается: <span class="mono">Доска.якт · Юла</span>. Парсер не реализован — заполни поля руками.</div>
</div>

<!-- Source chips -->
<div class="wrap">
    <div class="sources">
        {#each [['Доска.якт', 'doska.ykt.ru'], ['Юла', 'youla.ru']] as [name, host]}
            <div class="source">
                <div class="source-init">{name[0]}</div>
                <div class="source-body">
                    <div class="source-name">{name}</div>
                    <div class="source-host">{host}</div>
                </div>
            </div>
        {/each}
    </div>
</div>

<!-- Form -->
<Section title="Поля квартиры">
    <div class="wrap">
        <Card pad={14}>
            <div class="form">
                <label>
                    <span>Название*</span>
                    <input bind:value={title} placeholder="Лермонтова 58/24" />
                </label>
                <label class="full">
                    <span>Адрес*</span>
                    <input bind:value={address} placeholder="ул. Лермонтова, 58, кв. 24" />
                </label>
                <label>
                    <span>Тип</span>
                    <select bind:value={rooms}>
                        {#each ROOMS_OPTIONS as r}<option value={r}>{r}</option>{/each}
                    </select>
                </label>
                <label>
                    <span>Площадь м²</span>
                    <input type="number" bind:value={area} placeholder="52" />
                </label>
                <label>
                    <span>Этаж</span>
                    <input bind:value={floor} placeholder="3/5" />
                </label>
                <label>
                    <span>Район</span>
                    <input bind:value={district} placeholder="Сайсары" />
                </label>
                <label>
                    <span>Цена/ночь ₽*</span>
                    <input type="number" bind:value={price} placeholder="4280" />
                </label>
                <label class="full">
                    <span>URL обложки (одна картинка)</span>
                    <input bind:value={coverUrl} placeholder="https://..." />
                </label>
            </div>
        </Card>
    </div>
</Section>

<Section title="Собственник (визуально — не сохраняется)">
    <div class="wrap">
        <Card pad={14}>
            <input bind:value={ownerPhone} placeholder="Телефон собственника" class="owner-input" />
        </Card>
    </div>
</Section>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="actions">
    <button class="ghost" type="button" onclick={() => goto('/apartments')} disabled={saving}>Отмена</button>
    <button class="primary" type="button" onclick={save} disabled={saving}>
        {saving ? 'Сохраняю…' : 'Сохранить →'}
    </button>
</div>

<style>
    .wrap { padding: 0 20px 14px; }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        margin-bottom: 8px;
    }
    .url-field {
        width: 100%;
        height: 48px;
        border: 1.5px solid var(--accent);
        background: var(--card);
        border-radius: 8px;
        padding: 0 14px;
        font-family: var(--font-mono);
        font-size: 12px;
        color: var(--ink);
    }
    .hint {
        margin-top: 8px;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .mono { color: var(--muted); }

    .sources {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .source {
        padding: 12px;
        border: 1px solid var(--border);
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 10px;
        background: var(--card);
    }
    .source-init {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: var(--bg-subtle);
        color: var(--ink);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-weight: 700;
        font-size: 12px;
    }
    .source-body { flex: 1; }
    .source-name { font-size: 13px; font-weight: 600; color: var(--ink); }
    .source-host {
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        margin-top: 1px;
    }

    .form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .form .full { grid-column: 1 / -1; }
    .form label { display: flex; flex-direction: column; gap: 4px; }
    .form label span {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .form input, .form select {
        height: 42px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .owner-input {
        width: 100%;
        height: 42px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }

    .actions {
        padding: 8px 20px 24px;
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 10px;
    }
    .primary, .ghost {
        height: 50px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
