<script lang="ts">
	let {
		checked,
		onchange,
		label
	}: {
		checked: boolean;
		onchange: (val: boolean) => void;
		label: string;
	} = $props();
</script>

<label class="flex cursor-pointer items-center gap-3">
<button
		type="button"
		role="switch"
		aria-checked={checked}
		aria-label={label}
		onclick={() => onchange(!checked)}
		class="relative h-5 w-9 rounded-full transition-colors {checked ? 'bg-primary' : 'bg-muted'}"
	>
		<span
			class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-background transition-transform"
			class:translate-x-4={checked}
		></span>
	</button>
	<span class="text-sm text-foreground">{label}</span>
</label>
