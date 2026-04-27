<script>
    import { DEMO } from '$lib/demo.js';
</script>

{#if DEMO}
    <div class="demo-badge" aria-label="Demo instance">DEMO</div>
{/if}

<style>
    .demo-badge {
        position: fixed;
        top: 8px;
        right: 8px;
        z-index: 1000;
        background: var(--accent, #c33);
        color: #fff;
        font-family: var(--font-mono, monospace);
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.12em;
        padding: 4px 8px;
        border-radius: 3px;
        pointer-events: none;
    }
</style>
