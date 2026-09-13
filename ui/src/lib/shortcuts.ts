import type { ActiveTab } from '$lib/api/types';

export interface Shortcut {
	id: string;
	keys: string[];
	description: string;
	/** Short description shown as a hint on the triggering control. */
	hint?: string;
}

export type ShortcutId =
	| 'switch-generate'
	| 'switch-scrape'
	| 'switch-mutate'
	| 'run'
	| 'focus-url'
	| 'help'
	| 'close';

/** Returns true on macOS (where the primary modifier is ⌘/Meta). */
export function isMac(): boolean {
	return typeof navigator !== 'undefined' && /mac/i.test(navigator.platform);
}

/** The primary modifier label for the current OS: ⌘ on macOS, Ctrl elsewhere. */
export function modLabel(): string {
	return isMac() ? '⌘' : 'Ctrl';
}

/** True if a keydown is a primary-modifier combo (⌘ on mac, Ctrl elsewhere). */
export function isMod(e: KeyboardEvent): boolean {
	return isMac() ? e.metaKey : e.ctrlKey;
}

/** True when the event originates from a text-editable control. */
export function isTyping(e: KeyboardEvent): boolean {
	const t = e.target;
	if (t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement) {
		return true;
	}
	if (t instanceof HTMLElement && t.isContentEditable) {
		return true;
	}
	return false;
}

function keys(...parts: string[]): string[] {
	return parts;
}

export const SHORTCUTS: Shortcut[] = [
	{
		id: 'switch-generate',
		keys: ['1'],
		description: 'Switch to the Generate tab',
		hint: '1'
	},
	{
		id: 'switch-scrape',
		keys: ['2'],
		description: 'Switch to the Scrape tab',
		hint: '2'
	},
	{
		id: 'switch-mutate',
		keys: ['3'],
		description: 'Switch to the Mutate tab',
		hint: '3'
	},
	{
		id: 'run',
		keys: keys(modLabel(), 'Enter'),
		description: 'Run the active tab (Generate / Scrape / Mutate)',
		hint: `${modLabel()}↵`
	},
	{
		id: 'focus-url',
		keys: ['/'],
		description: 'Focus the target URL field'
	},
	{
		id: 'help',
		keys: ['?'],
		description: 'Show or hide the shortcuts reference'
	},
	{
		id: 'close',
		keys: ['Esc'],
		description: 'Close dialogs and popups'
	}
];

/** The shortcut used to switch to a given tab, or undefined. */
export function tabShortcut(tab: ActiveTab): string | undefined {
	return SHORTCUTS.find((s) => s.id === `switch-${tab}`)?.hint;
}