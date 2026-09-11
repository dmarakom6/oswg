<script lang="ts">
	import SegmentedControl from './SegmentedControl.svelte';
	import KeyValueList from './KeyValueList.svelte';
	import CookieFileField from './CookieFileField.svelte';
	import SessionStateField from './SessionStateField.svelte';

	type Cookie = { name: string; value: string };
	type Auth = { cookies: Cookie[]; cookieFile: string; sessionState: string };
	type Mode = 'none' | 'cookie' | 'file' | 'session';

	let {
		cookies,
		cookieFile,
		sessionState,
		onchange
	}: {
		cookies: Cookie[];
		cookieFile: string;
		sessionState: string;
		onchange: (value: Auth) => void;
	} = $props();

	let mode = $state<Mode>('none');

	function setMode(next: Mode) {
		mode = next;
		onchange({
			cookies: next === 'cookie' ? cookies : [],
			cookieFile: next === 'file' ? cookieFile : '',
			sessionState: next === 'session' ? sessionState : ''
		});
	}

	function setCookies(value: Cookie[]) {
		onchange({ cookies: value, cookieFile: '', sessionState: '' });
	}

	function setCookieFile(value: string) {
		onchange({ cookies: [], cookieFile: value, sessionState: '' });
	}

	function setSessionState(value: string) {
		onchange({ cookies: [], cookieFile: '', sessionState: value });
	}
</script>

<div class="space-y-3">
	<div class="space-y-1.5">
		<span class="block text-sm font-medium text-foreground">Authentication</span>
		<SegmentedControl
			value={mode}
			onchange={(v) => setMode(v as Mode)}
			options={[
				{ value: 'none', label: 'None' },
				{ value: 'cookie', label: 'Cookie' },
				{ value: 'file', label: 'cookies.txt' },
				{ value: 'session', label: 'Session file' }
			]}
		/>
	</div>

	{#if mode === 'cookie'}
		<KeyValueList kind="cookie" items={cookies} onchange={setCookies} />
	{:else if mode === 'file'}
		<CookieFileField value={cookieFile} onchange={setCookieFile} showLabel={false} />
	{:else if mode === 'session'}
		<SessionStateField value={sessionState} onchange={setSessionState} showLabel={false} />
	{:else}
		<p class="text-xs text-muted-foreground">
			No authentication. Choose Cookie, a cookies.txt export, or an
			<span class="font-mono">oswg login</span> session file.
		</p>
	{/if}
</div>
