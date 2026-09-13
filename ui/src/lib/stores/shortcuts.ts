import { writable } from 'svelte/store';

/** Increment to ask the visible config form to run. */
export const runSignal = writable(0);

/** Increment to ask the visible config form to focus its URL input. */
export const focusUrlSignal = writable(0);

/** Whether the keyboard-shortcuts reference dialog is open. */
export const helpOpen = writable(false);