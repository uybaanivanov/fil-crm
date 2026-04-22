<script>
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';

    const ROOMS_OPTIONS = ['Студия', '1-комн', '2-комн', '3+'];

    let url = $state('');
    let parsing = $state(false);
    let parseError = $state(null);

    let listing = $state(null);
    let title = $state('');
    let address = $state('');
    let rooms = $state('');
    let area = $state('');
    let floor = $state('');
    let district = $state('');
    let price = $state('');
    let coverUrl = $state('');
    let source = $state('');
    let sourceUrl = $state('');

    let saving = $state(false);
    let saveError = $state(null);

    async function doParse() {
        parseError = null;
        saveError = null;
        if (!url.trim()) { parseError = 'Вставь ссылку'; return; }
        parsing = true;
        try {
            const r = await api.post('/apartments/parse-url', { url: url.trim() });
            listing = r;
            title = r.title || '';
            address = r.address || '';
            rooms = r.rooms || '';
            area = r.area_m2 ? String(r.area_m2) : '';
            floor = r.floor || '';
            district = r.district || '';
            price = r.price_per_night ? String(r.price_per_night) : '';
            coverUrl = r.cover_url || '';
            source = r.source;
            sourceUrl = r.source_url;
        } catch (e) {
            parseError = e.message;
            listing = null;
        } finally {
            parsing = false;
        }
    }

    async function save() {
        saveError = null;
        const priceNum = parseInt(price, 10);
        if (!title || !address || !priceNum || priceNum <= 0) {
            saveError = 'Заполни название, адрес и цену (>0)';
            return;
        }
        saving = true;
        try {
            const payload = {
                title, address,
                price_per_night: priceNum,
                source, source_url: sourceUrl,
            };
            if (rooms) payload.rooms = rooms;
            if (area) payload.area_m2 = parseInt(area, 10);
            if (floor) payload.floor = floor;
            if (district) payload.district = district;
            if (coverUrl) payload.cover_url = coverUrl;
            const result = await api.post('/apartments', payload);
            goto(`/apartments/${result.id}`);
        } catch (e) {
            saveError = e.message;
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новая квартира" sub="Вставь ссылку — разберём и покажем поля"
    back="Отмена" backOnClick={() => goto('/apartments')} />

<div class="wrap">
    <div class="eyebrow">Ссылка на объявление</div>
    <input class="url-field" bind:value={url}
        placeholder="https://doska.ykt.ru/... или https://youla.ru/..."
        disabled={parsing} />
    <div class="hint">Поддержка: <span class="mono">Доска.якт · Юла</span> (трекер-ссылки mail.ru резолвим).</div>
    <button class="primary wide" type="button" onclick={doParse} disabled={parsing || !url.trim()}>
        {parsing ? 'Разбираю…' : 'Разобрать'}
    </button>
    {#if parseError}<div class="error-banner">{parseError}</div>{/if}
</div>

{#if listing}
    <Section title="Поля квартиры">
        <div class="wrap">
            <Card pad={14}>
                <div class="form">
                    <label>
                        <span>Название*</span>
                        <input bind:value={title} />
                    </label>
                    <label class="full">
                        <span>Адрес*</span>
                        <input bind:value={address} />
                    </label>
                    <label>
                        <span>Тип</span>
                        <select bind:value={rooms}>
                            <option value=""></option>
                            {#each ROOMS_OPTIONS as r}<option value={r}>{r}</option>{/each}
                        </select>
                    </label>
                    <label>
                        <span>Площадь м²</span>
                        <input type="number" bind:value={area} />
                    </label>
                    <label>
                        <span>Этаж</span>
                        <input bind:value={floor} />
                    </label>
                    <label>
                        <span>Район</span>
                        <input bind:value={district} />
                    </label>
                    <label>
                        <span>Цена/ночь ₽*</span>
                        <input type="number" bind:value={price} />
                    </label>
                    <label class="full">
                        <span>URL обложки</span>
                        <input bind:value={coverUrl} />
                    </label>
                </div>
            </Card>
        </div>
    </Section>

    {#if saveError}<div class="error-banner">{saveError}</div>{/if}

    <div class="actions">
        <button class="ghost" type="button" onclick={() => goto('/apartments')} disabled={saving}>Отмена</button>
        <button class="primary" type="button" onclick={save} disabled={saving}>
            {saving ? 'Сохраняю…' : 'Сохранить →'}
        </button>
    </div>
{/if}

<style>
    .wrap { padding: 0 20px 14px; }
    .eyebrow {
        font-family: var(--font-mono); font-size: 10px;
        letter-spacing: 0.1em; text-transform: uppercase;
        color: var(--faint); margin-bottom: 8px;
    }
    .url-field {
        width: 100%; height: 48px;
        border: 1.5px solid var(--accent); background: var(--card);
        border-radius: 8px; padding: 0 14px;
        font-family: var(--font-mono); font-size: 12px; color: var(--ink);
    }
    .url-field:disabled { opacity: 0.6; }
    .hint {
        margin-top: 8px; font-family: var(--font-mono);
        font-size: 10px; color: var(--faint);
    }
    .mono { color: var(--muted); }
    .wide { margin-top: 10px; width: 100%; height: 42px; border-radius: 8px; }
    .form { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .form .full { grid-column: 1 / -1; }
    .form label { display: flex; flex-direction: column; gap: 4px; }
    .form label span {
        font-family: var(--font-mono); font-size: 10px;
        letter-spacing: 0.1em; text-transform: uppercase; color: var(--faint);
    }
    .form input, .form select {
        height: 42px; background: var(--bg); border: 1px solid var(--border);
        border-radius: 6px; padding: 0 10px; color: var(--ink); font-size: 14px;
    }
    .actions {
        padding: 8px 20px 24px;
        display: grid; grid-template-columns: 1fr 2fr; gap: 10px;
    }
    .primary, .ghost {
        height: 50px; border-radius: 6px;
        font-size: 14px; font-weight: 600; cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
