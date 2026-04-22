<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, ApiError } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import CleaningDueDialog from '$lib/ui/CleaningDueDialog.svelte';
    import EditableField from '$lib/ui/EditableField.svelte';
    import ApartmentExpenses from '$lib/ui/ApartmentExpenses.svelte';
    import InlineEdit from '$lib/ui/InlineEdit.svelte';
    import HelpTip from '$lib/ui/HelpTip.svelte';
    import {
        fmtRub, fmtShortRub, fmtDate, fmtNights, fmtMonth,
        fmtDateTime, defaultCleaningDueAt, datetimeLocalToIso, isoToDatetimeLocal
    } from '$lib/format.js';

    const aptId = $derived(parseInt(page.params.id, 10));
    const currentMonth = new Date().toISOString().slice(0, 7);

    let apt = $state(null);
    let stats = $state(null);
    let bookings = $state([]);
    let clients = $state([]);
    let error = $state(null);
    let loading = $state(true);
    let dialogOpen = $state(false);
    let dialogDefault = $state('');
    let dialogError = $state(null);

    let editingBaseline = $state(false);
    let baselineRent = $state('');
    let baselineUtilities = $state('');
    let baselineError = $state(null);
    let baselineErrorField = $state(null); // 'rent' | 'utilities' | null
    let baselineRequired = $state(false);
    let baselineBlockEl = $state(null);

    const isOverdue = $derived(
        apt?.cleaning_due_at && new Date(apt.cleaning_due_at) < new Date()
    );

    async function load() {
        loading = true;
        try {
            const [a, s, b, c] = await Promise.all([
                api.get(`/apartments/${aptId}`),
                api.get(`/apartments/${aptId}/stats?month=${currentMonth}`),
                api.get('/bookings'),
                api.get('/clients')
            ]);
            apt = a;
            stats = s;
            bookings = b.filter(bb => bb.apartment_id === aptId);
            clients = c;
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    function startEditBaseline() {
        baselineRent = apt.monthly_rent ?? '';
        baselineUtilities = apt.monthly_utilities ?? '';
        baselineError = null;
        baselineErrorField = null;
        editingBaseline = true;
    }

    async function saveBaseline() {
        baselineError = null;
        baselineErrorField = null;
        const rent = parseInt(baselineRent, 10);
        if (!rent || rent < 0) {
            baselineError = 'Укажи аренду';
            baselineErrorField = 'rent';
            return;
        }
        try {
            const payload = { monthly_rent: rent };
            if (baselineUtilities !== '' && baselineUtilities !== null) {
                const u = parseInt(baselineUtilities, 10);
                if (!isNaN(u) && u >= 0) payload.monthly_utilities = u;
            }
            await api.patch(`/apartments/${aptId}`, payload);
            baselineRequired = false;
            editingBaseline = false;
            await load();
        } catch (e) {
            baselineError = e.message;
        }
    }

    async function patchField(field, value) {
        try {
            await api.patch(`/apartments/${aptId}`, { [field]: value });
            apt[field] = value;
            baselineRequired = false;
        } catch (e) {
            const msg = e?.message || '';
            if (msg.includes('monthly_rent')) {
                baselineRequired = true;
                queueMicrotask(() => {
                    baselineBlockEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
            }
            throw e;
        }
    }

    const today = new Date().toISOString().slice(0, 10);

    const currentGuest = $derived.by(() => {
        const b = bookings.find(x =>
            x.status === 'active' && x.check_in <= today && x.check_out > today
        );
        if (!b) return null;
        const client = clients.find(c => c.id === b.client_id);
        return { booking: b, client };
    });

    async function markClean() {
        try {
            await api.post(`/apartments/${aptId}/mark-clean`);
            await load();
        } catch (e) {
            error = e.message;
        }
    }
    function openCleaningDialog() {
        dialogDefault = apt.needs_cleaning && apt.cleaning_due_at
            ? isoToDatetimeLocal(apt.cleaning_due_at)
            : defaultCleaningDueAt(currentGuest);
        dialogError = null;
        dialogOpen = true;
    }

    async function submitCleaning(value) {
        try {
            await api.post(`/apartments/${aptId}/mark-dirty`, {
                cleaning_due_at: datetimeLocalToIso(value)
            });
            dialogOpen = false;
            await load();
        } catch (e) {
            dialogError = e.message;
        }
    }
</script>

<PageHead title={apt?.title ?? 'Квартира'} sub={apt?.address}
    back="Квартиры" backOnClick={() => goto('/apartments')} />

{#if error}
    <div class="error-banner">{error}</div>
{:else if loading || !apt}
    <div class="loading">Загрузка…</div>
{:else}
    <!-- Cover -->
    <div class="cover-wrap">
        {#if apt.cover_url}
            <img src={apt.cover_url} alt="" class="cover" />
        {:else}
            <div class="cover placeholder">
                {(apt.title || '?').slice(0, 2).toUpperCase()}
            </div>
        {/if}
        <div class="cover-chip">
            <Chip tone={currentGuest ? 'ok' : apt.needs_cleaning ? 'due' : 'draft'}>
                {currentGuest ? `Занята до ${fmtDate(currentGuest.booking.check_out)}` : apt.needs_cleaning ? 'Требует уборки' : 'Свободна'}
            </Chip>
        </div>
    </div>

    <!-- KPI -->
    {#if stats}
        <div class="kpis">
            {#each [
                { lbl: 'Ночей', val: stats.nights, meta: fmtMonth(currentMonth), term: null },
                { lbl: 'ADR', val: fmtShortRub(stats.adr), meta: '', term: 'adr' },
                { lbl: 'Выручка', val: fmtShortRub(stats.revenue), meta: Math.round((stats.utilization || 0) * 100) + '%', term: null }
            ] as k}
                <div class="kpi">
                    <div class="kpi-lbl">
                        {k.lbl}
                        {#if k.term}<HelpTip term={k.term}/>{/if}
                    </div>
                    <div class="kpi-val">{k.val}</div>
                    {#if k.meta}<div class="kpi-meta">{k.meta}</div>{/if}
                </div>
            {/each}
        </div>
    {/if}

    <!-- Current guest -->
    {#if currentGuest}
        <Section title="Гость">
            <div class="wrap">
                <Card pad={14}>
                    <button class="guest" type="button" onclick={() => currentGuest.client && goto(`/clients/${currentGuest.client.id}`)}>
                        <Avatar name={currentGuest.client?.full_name || '?'} size={44} accent="var(--accent)" />
                        <div class="guest-body">
                            <div class="guest-name">{currentGuest.client?.full_name || '—'}</div>
                            <div class="guest-phone">{currentGuest.client?.phone || ''}</div>
                        </div>
                    </button>
                    <div class="guest-range">
                        <span>{fmtDate(currentGuest.booking.check_in)} → {fmtDate(currentGuest.booking.check_out)}</span>
                        <span class="guest-sum">{fmtNights(currentGuest.booking.check_in, currentGuest.booking.check_out)} · {fmtRub(currentGuest.booking.total_price)}</span>
                    </div>
                </Card>
            </div>
        </Section>
    {/if}

    {#if baselineRequired}
        <div class="baseline-banner">
            Сначала заполни аренду в месяц ниже — без неё нельзя редактировать другие поля.
        </div>
    {/if}
    <div bind:this={baselineBlockEl}>
    <Section title="Обязательные суммы">
        <div class="wrap">
            <Card pad={14}>
                {#if editingBaseline}
                    <div class="bl-form">
                        <EditableField
                            label="Аренда помещения / мес"
                            required
                            error={baselineErrorField === 'rent' ? baselineError : null}
                        >
                            <input type="number" bind:value={baselineRent} placeholder="₽" />
                        </EditableField>
                        <EditableField
                            label="ЖКХ / мес"
                            required={false}
                            error={baselineErrorField === 'utilities' ? baselineError : null}
                        >
                            <input type="number" bind:value={baselineUtilities} placeholder="₽" />
                        </EditableField>
                        {#if baselineError && !baselineErrorField}
                            <div class="err-banner">{baselineError}</div>
                        {/if}
                        <div class="bl-actions">
                            <button type="button" class="ghost"
                                onclick={() => (editingBaseline = false)}>Отмена</button>
                            <button type="button" class="primary" onclick={saveBaseline}>Сохранить</button>
                        </div>
                    </div>
                {:else}
                    <div class="bl-row" class:empty={apt.monthly_rent == null}>
                        <span>Аренда / мес</span>
                        <span>{apt.monthly_rent != null ? fmtRub(apt.monthly_rent) : '— не заполнено'}</span>
                    </div>
                    <div class="bl-row" class:empty={apt.monthly_utilities == null}>
                        <span>ЖКХ / мес</span>
                        <span>{apt.monthly_utilities != null ? fmtRub(apt.monthly_utilities) : '— не заполнено'}</span>
                    </div>
                    <button type="button" class="ghost bl-edit" onclick={startEditBaseline}>
                        {apt.monthly_rent == null ? 'Заполнить аренду' : 'Изменить'}
                    </button>
                {/if}
            </Card>
        </div>
    </Section>
    </div>

    <Section title="Расходы">
        <ApartmentExpenses apartmentId={aptId} />
    </Section>

    <!-- Характеристики -->
    <Section title="Характеристики">
        <div class="wrap">
            <Card pad={0}>
                <div class="ch-row">
                    <span class="ch-key">Название</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.title}
                            type="text"
                            placeholder="Название"
                            onSave={v => patchField('title', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Адрес</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.address}
                            type="text"
                            placeholder="Адрес"
                            onSave={v => patchField('address', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Тип</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.rooms}
                            type="text"
                            placeholder="Напр. 1-комн"
                            onSave={v => patchField('rooms', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Площадь</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.area_m2}
                            type="number"
                            placeholder="— м²"
                            format={v => v + ' м²'}
                            onSave={v => patchField('area_m2', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Этаж</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.floor}
                            type="text"
                            placeholder="Этаж"
                            onSave={v => patchField('floor', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Район</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.district}
                            type="text"
                            placeholder="Район"
                            onSave={v => patchField('district', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Цена/ночь</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.price_per_night}
                            type="number"
                            placeholder="₽"
                            format={fmtRub}
                            onSave={v => patchField('price_per_night', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Позывной</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.callsign}
                            type="text"
                            placeholder="позывной"
                            onSave={v => patchField('callsign', v)}
                        />
                    </span>
                </div>
                <div class="ch-row">
                    <span class="ch-key">Обложка</span>
                    <span class="ch-val">
                        <InlineEdit
                            value={apt.cover_url}
                            type="text"
                            placeholder="URL картинки"
                            onSave={v => patchField('cover_url', v)}
                        />
                    </span>
                </div>
                <div class="ch-row last">
                    <span class="ch-key">Нужна уборка</span>
                    <span class="ch-val">
                        {apt.needs_cleaning
                            ? (apt.cleaning_due_at ? 'К ' + fmtDateTime(apt.cleaning_due_at) : 'Да')
                            : 'Нет'}
                    </span>
                    {#if isOverdue}
                        <span class="overdue"><Chip tone="late">Просрочено</Chip></span>
                    {/if}
                </div>
            </Card>
        </div>
    </Section>

    <!-- Actions -->
    <div class="actions">
        <button class="primary" type="button" onclick={() => goto(`/bookings/new?apartment_id=${aptId}`)}>
            + Бронь
        </button>
        {#if apt.needs_cleaning}
            <button class="ghost" type="button" onclick={openCleaningDialog}>Изменить уборку</button>
            <button class="primary" type="button" onclick={markClean}>Закрыть уборку ✓</button>
        {:else}
            <button class="ghost" type="button" onclick={openCleaningDialog}>Требует уборки</button>
        {/if}
    </div>

    <CleaningDueDialog
        open={dialogOpen}
        defaultValue={dialogDefault}
        errorText={dialogError}
        onSubmit={submitCleaning}
        onCancel={() => (dialogOpen = false)}
    />
{/if}

<style>
    .loading { padding: 40px 20px; color: var(--faint); text-align: center; }
    .wrap { padding: 0 20px 14px; }
    .cover-wrap {
        margin: 0 20px 16px;
        height: 170px;
        border-radius: 10px;
        overflow: hidden;
        position: relative;
        background: var(--bg-subtle);
    }
    .cover {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .cover.placeholder {
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 34px;
        font-weight: 700;
        color: var(--faint);
    }
    .cover-chip {
        position: absolute;
        top: 12px;
        left: 12px;
    }

    .kpis {
        padding: 0 20px 14px;
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--card);
        margin: 0 20px 16px;
        overflow: hidden;
    }
    .kpi {
        padding: 12px 10px;
        text-align: center;
        border-right: 1px solid var(--border);
    }
    .kpi:last-child { border-right: none; }
    .kpi-lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--faint);
    }
    .kpi-val {
        font-family: var(--font-mono);
        font-size: 14px;
        font-weight: 600;
        margin-top: 4px;
        color: var(--ink);
    }
    .kpi-meta {
        font-family: var(--font-mono);
        font-size: 9px;
        color: var(--faint);
        margin-top: 2px;
    }

    .guest {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 12px;
        background: transparent;
        border: none;
        padding: 0 0 12px;
        cursor: pointer;
        text-align: left;
    }
    .guest-body { flex: 1; min-width: 0; }
    .guest-name { font-size: 15px; font-weight: 600; color: var(--ink); }
    .guest-phone { font-family: var(--font-mono); font-size: 11px; color: var(--faint); margin-top: 2px; }
    .guest-range {
        display: flex;
        justify-content: space-between;
        padding: 10px 12px;
        background: var(--bg-subtle);
        border-radius: 6px;
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
    }
    .guest-sum { color: var(--ink); font-weight: 600; }

    .ch-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-soft);
    }
    .ch-row.last { border-bottom: none; }
    .ch-key {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--faint);
        text-transform: uppercase;
    }
    .ch-val { font-size: 13px; color: var(--ink); font-weight: 500; }

    .actions {
        padding: 0 20px 24px;
        display: flex;
        gap: 10px;
    }
    .primary, .ghost {
        flex: 1;
        height: 46px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
    .overdue { margin-left: 8px; }

    .bl-form { display: flex; flex-direction: column; gap: 10px; }
    .bl-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 6px; }
    .bl-row {
        display: flex; justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-soft);
        font-size: 13px;
    }
    .bl-row:last-of-type { border-bottom: none; }
    .bl-row.empty { color: var(--danger, #c33); }
    .bl-edit { margin-top: 10px; width: 100%; }
    .err-banner {
        background: var(--danger-bg, #fde);
        color: var(--danger, #c33);
        padding: 6px 8px; border-radius: 4px;
        font-size: 12px;
    }
    .baseline-banner {
        margin: 0 20px 12px;
        padding: 10px 12px;
        background: var(--danger-bg, #fde);
        color: var(--danger, #c33);
        border-radius: 6px;
        font-size: 12px;
        line-height: 1.4;
    }
</style>
