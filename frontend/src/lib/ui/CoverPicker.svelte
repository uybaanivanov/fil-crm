<script>
    import { api } from '$lib/api.js';

    let { apartmentId, cover, onChange } = $props();

    let busy = $state(false);
    let err = $state(null);
    let inputEl = $state(null);

    function pick() { inputEl?.click(); }

    async function onFile(e) {
        const f = e.target.files?.[0];
        e.target.value = '';
        if (!f) return;
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) {
            err = 'Только jpeg/png/webp'; return;
        }
        if (f.size > 5 * 1024 * 1024) {
            err = 'Файл больше 5 МБ'; return;
        }
        busy = true; err = null;
        try {
            const fd = new FormData();
            fd.append('file', f);
            const r = await api.postForm(`/apartments/${apartmentId}/cover`, fd);
            onChange(r.cover_url);
        } catch (e) {
            err = e.message || 'Ошибка загрузки';
        } finally {
            busy = false;
        }
    }

    async function remove() {
        if (!confirm('Удалить обложку?')) return;
        busy = true; err = null;
        try {
            await api.delete(`/apartments/${apartmentId}/cover`);
            onChange(null);
        } catch (e) {
            err = e.message || 'Ошибка удаления';
        } finally {
            busy = false;
        }
    }
</script>

<div class="cover-picker">
    {#if cover}
        <div class="thumb" style="background-image:url({cover})">
            <div class="ovr">
                <button type="button" onclick={pick} disabled={busy}>Заменить</button>
                <button type="button" class="danger" onclick={remove} disabled={busy}>Удалить</button>
            </div>
        </div>
    {:else}
        <button type="button" class="placeholder" onclick={pick} disabled={busy}>
            <span class="icon">📷</span>
            <span>Загрузить обложку</span>
        </button>
    {/if}
    <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        bind:this={inputEl}
        onchange={onFile}
        hidden
    />
    {#if busy}<div class="hint">Загрузка…</div>{/if}
    {#if err}<div class="err">{err}</div>{/if}
</div>

<style>
    .cover-picker { width: 100%; height: 100%; }
    .thumb {
        width: 100%;
        height: 100%;
        background-size: cover;
        background-position: center;
        position: relative;
        overflow: hidden;
        border-radius: 10px;
    }
    .ovr {
        position: absolute; inset: 0;
        background: rgba(0,0,0,0.45);
        opacity: 0;
        transition: opacity 120ms ease;
        display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    .thumb:hover .ovr, .thumb:focus-within .ovr { opacity: 1; }
    .ovr button {
        background: #fff; border: none; padding: 6px 12px; border-radius: 6px;
        font-size: 12px; cursor: pointer;
    }
    .ovr .danger { color: #c33; }
    .placeholder {
        width: 100%;
        height: 100%;
        border: 1px dashed var(--border);
        border-radius: 10px;
        background: transparent;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        gap: 8px;
        color: var(--faint);
        font-size: 13px;
        cursor: pointer;
    }
    .placeholder:hover { color: var(--ink); border-color: var(--ink); }
    .icon { font-size: 28px; }
    .hint { font-size: 11px; color: var(--faint); padding-top: 4px; }
    .err { font-size: 11px; color: #c33; padding-top: 4px; }
</style>
