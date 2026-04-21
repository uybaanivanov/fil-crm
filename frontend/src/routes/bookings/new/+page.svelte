<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Searchbar from '$lib/ui/Searchbar.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import { fmtRub, fmtNights } from '$lib/format.js';

    // Quick-param support: /bookings/new?client_id=N&apartment_id=M
    const preClientId = $derived(parseInt(page.url.searchParams.get('client_id') || '', 10) || null);
    const preApartmentId = $derived(parseInt(page.url.searchParams.get('apartment_id') || '', 10) || null);

    let apartments = $state([]);
    let clients = $state([]);
    let error = $state(null);
    let saving = $state(false);

    let apartmentId = $state(null);
    let clientId = $state(null);
    let checkIn = $state('');
    let checkOut = $state('');
    let totalPrice = $state('');
    let notes = $state('');
    let clientQuery = $state('');

    // Inline client creation
    let createOpen = $state(false);
    let newName = $state('');
    let newPhone = $state('');
    let newSource = $state('Прямая');

    onMount(async () => {
        try {
            const [a, c] = await Promise.all([
                api.get('/apartments'),
                api.get('/clients')
            ]);
            apartments = a;
            clients = c;
            if (preApartmentId) apartmentId = preApartmentId;
            if (preClientId) clientId = preClientId;
        } catch (e) {
            error = e.message;
        }
    });

    const apt = $derived(apartments.find(a => a.id === apartmentId) || null);
    const client = $derived(clients.find(c => c.id === clientId) || null);

    const nights = $derived.by(() => {
        if (!checkIn || !checkOut) return 0;
        return Math.round((new Date(checkOut) - new Date(checkIn)) / 86400000);
    });

    // Авто-пересчёт цены при смене дат/квартиры (если пользователь не редактировал руками)
    let priceManuallyEdited = $state(false);
    $effect(() => {
        if (priceManuallyEdited) return;
        if (apt && nights > 0) {
            totalPrice = String(apt.price_per_night * nights);
        }
    });

    const visibleClients = $derived(
        clientQuery
            ? clients.filter(c =>
                (c.full_name || '').toLowerCase().includes(clientQuery.toLowerCase())
                || (c.phone || '').includes(clientQuery)
            ).slice(0, 6)
            : clients.slice(-5).reverse()
    );

    async function createClient() {
        if (!newName || !newPhone) {
            error = 'Имя и телефон обязательны';
            return;
        }
        try {
            const c = await api.post('/clients', {
                full_name: newName,
                phone: newPhone,
                source: newSource || null
            });
            clients = [...clients, c];
            clientId = c.id;
            createOpen = false;
            newName = '';
            newPhone = '';
        } catch (e) {
            error = e.message;
        }
    }

    async function save() {
        error = null;
        if (!apartmentId) return (error = 'Выбери квартиру');
        if (!clientId) return (error = 'Выбери гостя');
        if (!checkIn || !checkOut) return (error = 'Укажи даты');
        const price = parseInt(totalPrice, 10);
        if (!price || price <= 0) return (error = 'Сумма должна быть > 0');
        if (new Date(checkOut) <= new Date(checkIn)) return (error = 'Выезд должен быть позже заезда');

        saving = true;
        try {
            const result = await api.post('/bookings', {
                apartment_id: apartmentId,
                client_id: clientId,
                check_in: checkIn,
                check_out: checkOut,
                total_price: price,
                notes: notes || null
            });
            goto(`/bookings/${result.id}`);
        } catch (e) {
            error = e.message;
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новая бронь" sub="Квартира → даты → гость → сумма"
    back="Отмена" backOnClick={() => goto('/bookings')} />

<!-- Apartment picker -->
<Section title="Квартира">
    <div class="wrap">
        {#if apt}
            <button class="selected" type="button" onclick={() => (apartmentId = null)}>
                <div class="sel-label">
                    <div class="sel-title">{apt.title}</div>
                    <div class="sel-meta">{apt.address}</div>
                </div>
                <span class="change">Сменить</span>
            </button>
        {:else}
            <div class="apt-list">
                {#each apartments as a}
                    <button class="pick" onclick={() => (apartmentId = a.id)} type="button">
                        <div class="pick-t">{a.title}</div>
                        <div class="pick-m">{a.address} · {fmtRub(a.price_per_night)}/ноч</div>
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</Section>

<!-- Dates -->
<Section title="Даты">
    <div class="wrap">
        <Card pad={14}>
            <div class="dates-form">
                <label>
                    <span>Заезд · 14:00</span>
                    <input type="date" bind:value={checkIn} />
                </label>
                <label>
                    <span>Выезд · 12:00</span>
                    <input type="date" bind:value={checkOut} />
                </label>
            </div>
            {#if nights > 0}
                <div class="nights-info">
                    <span>{fmtNights(checkIn, checkOut)}</span>
                </div>
            {/if}
        </Card>
    </div>
</Section>

<!-- Guest picker -->
<Section title="Гость">
    <div class="wrap">
        {#if client}
            <button class="selected" type="button" onclick={() => (clientId = null)}>
                <Avatar name={client.full_name} size={36} />
                <div class="sel-label">
                    <div class="sel-title">{client.full_name}</div>
                    <div class="sel-meta">{client.phone}</div>
                </div>
                <span class="change">Сменить</span>
            </button>
        {:else}
            <Searchbar bind:value={clientQuery} placeholder="Поиск имя / телефон…" />
            <div class="guest-list">
                {#each visibleClients as c}
                    <button class="pick" onclick={() => (clientId = c.id)} type="button">
                        <Avatar name={c.full_name} size={30} />
                        <div>
                            <div class="pick-t">{c.full_name}</div>
                            <div class="pick-m">{c.phone}</div>
                        </div>
                    </button>
                {/each}
            </div>
            <button class="create-toggle" onclick={() => (createOpen = !createOpen)} type="button">
                {createOpen ? '× Свернуть' : '+ Создать нового'}
            </button>
            {#if createOpen}
                <Card pad={12}>
                    <div class="create-form">
                        <label><span>Имя</span><input bind:value={newName} /></label>
                        <label><span>Телефон</span><input bind:value={newPhone} /></label>
                        <label>
                            <span>Источник</span>
                            <select bind:value={newSource}>
                                <option>Доска.якт</option>
                                <option>Юла</option>
                                <option>Прямая</option>
                            </select>
                        </label>
                        <button class="primary small" type="button" onclick={createClient}>Добавить</button>
                    </div>
                </Card>
            {/if}
        {/if}
    </div>
</Section>

<!-- Сумма -->
{#if apt && nights > 0}
    <Section title="Сумма">
        <div class="wrap">
            <Card pad={14}>
                <div class="calc">
                    <span>{nights} × {fmtRub(apt.price_per_night)} ночь</span>
                    <input
                        type="number"
                        class="total"
                        bind:value={totalPrice}
                        oninput={() => (priceManuallyEdited = true)}
                    />
                </div>
                <div class="calc-hint">ручное изменение переопределяет авто-расчёт</div>
            </Card>
        </div>
    </Section>
{/if}

<!-- Заметка -->
<Section title="Заметка (опционально)">
    <div class="wrap">
        <textarea class="notes" bind:value={notes} placeholder="…"></textarea>
    </div>
</Section>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="actions">
    <button class="ghost" type="button" onclick={() => goto('/bookings')} disabled={saving}>Отмена</button>
    <button class="primary" type="button" onclick={save} disabled={saving}>
        {saving ? 'Сохраняю…' : 'Создать бронь →'}
    </button>
</div>

<style>
    .wrap { padding: 0 20px 14px; }

    .selected {
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
    .sel-label { flex: 1; min-width: 0; }
    .sel-title { font-size: 14px; font-weight: 600; color: var(--ink); }
    .sel-meta { font-family: var(--font-mono); font-size: 10px; color: var(--faint); margin-top: 2px; text-transform: uppercase; }
    .change { font-size: 12px; color: var(--accent); font-weight: 500; }

    .apt-list, .guest-list { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
    .pick {
        width: 100%;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 10px 12px;
        display: flex;
        align-items: center;
        gap: 10px;
        text-align: left;
        cursor: pointer;
    }
    .pick:hover { background: var(--card-hi); }
    .pick-t { font-size: 13px; font-weight: 600; color: var(--ink); }
    .pick-m { font-family: var(--font-mono); font-size: 10px; color: var(--faint); margin-top: 2px; }

    .dates-form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .dates-form label { display: flex; flex-direction: column; gap: 4px; }
    .dates-form label span {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .dates-form input {
        height: 42px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .nights-info {
        margin-top: 12px;
        padding: 10px 12px;
        background: var(--bg-subtle);
        border-radius: 6px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--ink);
        font-weight: 600;
    }

    .create-toggle {
        margin-top: 10px;
        width: 100%;
        padding: 10px;
        background: transparent;
        border: 1px dashed var(--border);
        color: var(--muted);
        font-size: 12px;
        border-radius: 6px;
        cursor: pointer;
    }
    .create-form {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .create-form label { display: flex; flex-direction: column; gap: 4px; }
    .create-form label span {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
    }
    .create-form input, .create-form select {
        height: 38px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-size: 14px;
    }
    .small { height: 40px !important; margin-top: 4px; }

    .calc {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
    }
    .calc span {
        font-family: var(--font-mono);
        font-size: 12px;
        color: var(--muted);
    }
    .total {
        width: 130px;
        height: 40px;
        background: var(--bg);
        border: 1.5px solid var(--accent);
        border-radius: 6px;
        padding: 0 10px;
        color: var(--ink);
        font-family: var(--font-mono);
        font-weight: 600;
        font-size: 14px;
        text-align: right;
    }
    .calc-hint {
        margin-top: 6px;
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        text-transform: uppercase;
    }

    .notes {
        width: 100%;
        min-height: 60px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 10px;
        color: var(--ink);
        font-family: var(--font-sans);
        font-size: 13px;
        resize: vertical;
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
