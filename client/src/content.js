import { writable } from 'svelte/store';
import api from './api.js'


export const content = writable({
	'site-title': '',
	'site-home-logged-out': '',
	'site-home-empty': '',
	'site-home-normal': '',
});

export async function update() {
	const newContent = await api.getContent([
		'site-title',
		'site-home-logged-out',
		'site-home-empty',
		'site-home-normal',
	])
	content.set(newContent)
}

update()