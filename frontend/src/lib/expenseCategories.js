// value = то что летит в БД; label = отображается в UI.
export const EXPENSE_CATEGORIES = [
    { value: 'rent',      label: 'Аренда' },
    { value: 'utilities', label: 'ЖКХ' },
    { value: 'internet',  label: 'Интернет' },
    { value: 'repair',    label: 'Ремонт' },
    { value: 'furniture', label: 'Мебель' },
    { value: 'supplies',  label: 'Расходники' },
    { value: 'other',     label: 'Прочее' },
];

export function categoryLabel(value) {
    const found = EXPENSE_CATEGORIES.find(c => c.value === value);
    return found ? found.label : value;
}
