import { writable } from 'svelte/store';
import api from './api.js'


function createContent() {
	const { subscribe, set } = writable({
		'site-title': '',
		'site-home-logged-out': '',
		'site-home-empty': '',
		'site-home-normal': '',
	});
	const contentStore = {
		subscribe,
		async update() {
			set(await api.getContent([
				'site-title',
				'site-home-logged-out',
				'site-home-empty',
				'site-home-normal',
			]))
		}
	}
	contentStore.update()
	return contentStore
}

export const content = createContent()