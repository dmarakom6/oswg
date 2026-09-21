<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import { templatesVersion, bumpTemplates } from '$lib/stores/templates';
	import type { PresetsResponse, TemplateInfo } from '$lib/api/types';

	let {
		type,
		onApply,
		onSave
	}: {
		type: 'generate' | 'scrape';
		onApply: (config: Record<string, unknown>) => void;
		onSave: (name: string) => Promise<void>;
	} = $props();

	let presets = $state<PresetsResponse['presets']>({});
	let templates = $state<TemplateInfo[]>([]);
	let name = $state('');

	async function loadTemplates() {
		try {
			const res = await endpoints.listTemplates();
			templates = res.templates;
		} catch {
			templates = [];
		}
	}

	$effect(() => {
		endpoints.getPresets().then((r) => (presets = r.presets));
		loadTemplates();
		void $templatesVersion;
	});

	async function applyPreset(value: string) {
		if (!value || !presets[value]) return;
		onApply({ ...presets[value] });
	}

	async function applyTemplate(value: string) {
		if (!value) return;
		try {
			const record = await endpoints.getTemplate(value);
			onApply({ ...record.config });
		} catch {
			// template may have been deleted; refresh the list
			loadTemplates();
		}
	}

	async function save() {
		if (!name.trim()) return;
		await onSave(name.trim());
		name = '';
		bumpTemplates();
	}
</script>

<div class="space-y-3 rounded-md border border-border bg-muted/20 p-3">
	<p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
		Templates & Presets
	</p>

	<div class="space-y-1.5">
		<label for="template-preset" class="block text-sm font-medium text-foreground">Preset</label>
		<select
			id="template-preset"
			value=""
			onchange={(e) => {
				const value = e.currentTarget.value;
				e.currentTarget.value = '';
				applyPreset(value);
			}}
			class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
		>
			<option value="">None</option>
			{#each Object.keys(presets) as presetName}
				<option value={presetName}>{presetName}</option>
			{/each}
		</select>
	</div>

	<div class="space-y-1.5">
		<label for="template-select" class="block text-sm font-medium text-foreground">Template</label>
		<select
			id="template-select"
			value=""
			onchange={(e) => {
				const value = e.currentTarget.value;
				e.currentTarget.value = '';
				applyTemplate(value);
			}}
			class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
		>
			<option value="">None</option>
			{#each templates as t}
				<option value={t.name}>{t.name} ({t.type})</option>
			{/each}
		</select>
	</div>

	<div class="flex gap-2">
		<input
			id="template-name"
			value={name}
			oninput={(e) => (name = e.currentTarget.value)}
			placeholder="Template name"
			class="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
		/>
		<button
			type="button"
			onclick={save}
			disabled={!name.trim()}
			class="shrink-0 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
		>
			Save
		</button>
	</div>
</div>