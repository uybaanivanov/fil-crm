<script>
    let {
        open = false,
        onClose
    } = $props();

    let step = $state('choose'); // 'choose' | 'wip'

    $effect(() => {
        if (!open) {
            step = 'choose';
        }
    });

    function pick(_kind) {
        // _kind: 'business' | 'personal' — пока не используется (бэк появится позже)
        step = 'wip';
    }
</script>

{#if open}
    <div class="backdrop" onclick={onClose} role="presentation"></div>
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Сделать договор">
        <button class="close" type="button" onclick={onClose} aria-label="Закрыть">×</button>
        {#if step === 'choose'}
            <div class="title">Для кого делаем договор?</div>
            <div class="choices">
                <button class="choice" type="button" onclick={() => pick('business')}>
                    Командированный
                </button>
                <button class="choice" type="button" onclick={() => pick('personal')}>
                    Не командированный
                </button>
            </div>
        {:else}
            <div class="title">Скоро</div>
            <div class="wip">
                Генерация договора скоро появится. Сейчас эта кнопка — заглушка:
                выбор сохранён, сам документ подтянем позже.
            </div>
            <div class="actions">
                <button type="button" class="primary" onclick={onClose}>Понятно</button>
            </div>
        {/if}
    </div>
{/if}

<style>
    .backdrop {
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.4);
        z-index: 1000;
    }
    .dialog {
        position: fixed;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: min(360px, calc(100vw - 40px));
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px 16px 16px;
        z-index: 1001;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }
    .close {
        position: absolute;
        top: 6px; right: 8px;
        background: transparent;
        border: none;
        color: var(--faint);
        font-size: 22px;
        line-height: 1;
        cursor: pointer;
        padding: 4px 8px;
    }
    .close:hover { color: var(--ink); }
    .title {
        font-size: 15px;
        font-weight: 600;
        color: var(--ink);
        padding-right: 24px;
    }
    .choices {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .choice {
        padding: 16px 12px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        cursor: pointer;
        font-family: inherit;
    }
    .choice:hover {
        background: var(--card-hi);
        border-color: var(--accent);
    }
    .wip {
        font-size: 13px;
        line-height: 1.5;
        color: var(--ink2);
    }
    .actions {
        display: flex;
        justify-content: flex-end;
    }
    .primary {
        padding: 10px 18px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 6px;
        background: var(--accent);
        color: #fff;
        border: none;
        cursor: pointer;
    }
    .primary:hover { background: var(--accent2); }
</style>
