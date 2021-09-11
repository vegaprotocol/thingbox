import requests
import json
from dataclasses import asdict, dataclass
from base58 import b58decode
from base64 import b64encode
from nacl.public import SealedBox, PublicKey


@dataclass
class Item:
	target_type: str
	target_id: str
	category: str
	data_encrypted_b64: str
	template: str
	batch: str = None


def server_url(server_base_url, path):
	server_base_url = server_base_url if server_base_url[-1] != '/' else server_base_url[:-1]
	return server_base_url + path


def get_public_key(server_base_url):
	res = requests.get(url=server_url(server_base_url, '/public-key'))
	if res.status_code == 200:
		json = res.json()
		return json['public_key_b58']
	else:
		raise Exception(f'error {res.status_code}')


def encrypt(plaintext, public_key_b58):
	box = SealedBox(PublicKey(b58decode(public_key_b58)))
	ciphertext = box.encrypt(plaintext=plaintext.encode())
	return b64encode(ciphertext).decode('utf-8')


def add_item(
		server_base_url, 
		auth_token, 
		target_type, 
		target_id, 
		category, 
		data_plaintext, 
		template_id, 
		batch_id=None,
		close_batch=True):
	public_key = get_public_key(server_base_url)
	data_encrypted_b64 = encrypt(data_plaintext, public_key)
	item = Item(
			target_type=target_type, 
			target_id=target_id, 
			category=category, 
			data_encrypted_b64=data_encrypted_b64, 
			template=template_id)
	res = requests.post(
		url=server_url(server_base_url, '/items'),
		params=dict(batch=batch_id, close_batch=close_batch) if batch_id or not close_batch else None,
		headers=dict(Authorization=f'Bearer {auth_token}'),
		json=asdict(item))
	if res.status_code == 200:
		result = res.json()
		return result
	else:
		raise Exception(f'error: {repr(res)}')


def add_items(
		server_base_url, 
		auth_token, 
		items, 
		target_type_field='target_type',
		target_id_field='target_id',
		category_field='category',
		template_id_field='template',
		override_target_type=None, 
		override_target_id=None,
		override_category=None,
		override_template_id=None,
		global_data={},
		dry_run=False,
		log_fn=print):
	batch_id = None
	for i, item_data in enumerate(items):
		target_type = override_target_type or item_data[target_type_field] 
		target_id = override_target_id or item_data[target_id_field]
		category = override_category or item_data[category_field]
		template_id = override_template_id or item_data[template_id_field]
		full_data = { **global_data, **item_data }
		if dry_run:
			log_fn(f'#{i} [DRY_RUN]: {target_type} {target_id} ({category}/{template_id}): {repr(full_data)}')
		else:
			is_last_item = i == len(items) - 1
			try:
				result = add_item(
					server_base_url=server_base_url,
					auth_token=auth_token, 
					target_type=target_type, 
					target_id=target_id, 
					category=category,
					data_plaintext=json.dumps(full_data),
					template_id=template_id,
					batch_id=batch_id,
					close_batch=is_last_item)
				if result and 'batch' in result: batch_id = result['batch']
				if 'success' in result and not result['success']: raise Exception(repr(result))
				log_fn(f'{batch_id}#{i}: CREATED {target_type} {target_id} ({category}: {template_id})')
			except Exception as e:
				log_fn(f'{batch_id or "????????"}#{i}: ERORR {target_type} {target_id} ({category}: {template_id}): {repr(e)}')
