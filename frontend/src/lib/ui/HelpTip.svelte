<script>
    import { GLOSSARY } from '$lib/glossary.js';

    let { term } = $props();
    let open = $state(false);
    let btn = $state(null);

    const entry = $derived(GLOSSARY[term]);

    function toggle(e) {
        e.stopPropagation();
        open = !open;
    }

    function onWindowClick(e) {
        if (!open) return;
        if (btn && btn.contains(e.target)) return;
        open = false;
    }

    function onKey(e) {
        if (e.key === 'Escape') open = false;
    }

    $effect(() => {
        if (typeof window === 'undefined') return;
        window.addEventListener('click', onWindowClick);
        window.addEventListener('keydown', onKey);
        return () => {
            window.removeEventListener('click', onWindowClick);
            window.removeEventListener('keydown', onKey);
        };
    });
</script>

{#if entry}
    <span class="wrap">
        <button
            type="button"
            class="ico"
            bind:this={btn}
            onclick={toggle}
            aria-label="Что это?"
        >ⓘ</button>
        {#if open}
            <span class="pop">
                <b>{entry.title}</b>
                <span class="body">{entry.body}</span>
            </span>
        {/if}
    </span>
{/if}

<style>
    .wrap { position: relative; display: inline-flex; align-items: center; gap: 4px; }
    .ico {
        font-size: 12px;
        color: var(--faint);
        background: transparent;
        border: none;
        padding: 0 2px;
        cursor: pointer;
        line-height: 1;
    }
    .ico:hover { color: var(--ink); }
    .pop {
        position: absolute;
        top: calc(100% + 4px);
        left: 0;
        z-index: 50;
        min-width: 200px;
        max-width: 260px;
        padding: 8px 10px;
        background: var(--bg, #fff);
        color: var(--ink);
        border: 1px solid var(--border);
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        font-size: 12px;
        line-height: 1.4;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .pop b { font-size: 11px; }
    .body { color: var(--faint); }
</style>
