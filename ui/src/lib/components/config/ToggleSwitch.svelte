<script lang="ts">
	let {
		checked,
		onchange,
		label,
		disabled = false
	}: {
		checked: boolean;
		onchange: (val: boolean) => void;
		label: string;
		disabled?: boolean;
	} = $props();
</script>

<label class="flex cursor-pointer items-center gap-3 {disabled ? 'cursor-not-allowed opacity-50' : ''}">
<button
		type="button"
		role="switch"
		aria-checked={checked}
		aria-label={label}
		disabled={disabled}
		onclick={() => onchange(!checked)}
		class="relative h-5 w-9 rounded-full transition-colors {disabled ? 'cursor-not-allowed' : ''} {checked ? 'bg-primary' : 'bg-muted'}"
	>
		<span
			class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-background transition-transform"
			class:translate-x-4={checked}
		></span>
	</button>
	<span class="text-sm text-foreground">{label}</span>
</label>
