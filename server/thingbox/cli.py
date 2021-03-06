import click
import sys
import json
import csv as csv_lib

from thingbox import client


@click.group()
def cli():
	pass


def global_options(server=True, auth_token=True):
	def global_options_wrapper(fn):
		if server: fn = click.option('-s', '--server', required=True, envvar='TB_SERVER', help='Server API base URL')(fn)
		if auth_token: fn = click.option('-a', '--auth-token', required=True, envvar='TB_TOKEN', help='Server API token')(fn)
		return fn
	return global_options_wrapper


@cli.command(help='Encrypt data to the server\'s public key')
@global_options(auth_token=False)
@click.option('-d', '--data')
@click.argument('data_file', type=click.File('rb'), required=False, default=sys.stdin)
def encrypt(server, data, data_file):
	public_key = client.get_public_key(server)
	if data is None: data = data_file.read()
	ciphertext = client.encrypt(plaintext=data, public_key_b58=public_key)
	click.echo(ciphertext)


@cli.command(help='Generate a server private (secret) key')
def generate_key():
	private_key = client.generate_private_key()
	click.echo(private_key)


@cli.command(help="Encrypt and add an item for a given user ID")
@global_options()
@click.option(
		'-u', '--target-user', 
		nargs=2, type=str, required=True, 
		help='Target user, e.g.: --target-user twitter 44196397')
@click.option('-t', '--template', required=True, default=None, help='Template ID to render with')
@click.option('-c', '--category', required=True, default=None, help='Item category metadata')
@click.option('-d', '--data', required=False, default=None, help='Item data in plaintext JSON')
@click.argument('data_file', type=click.File('rb'), required=False, default=sys.stdin)
def add_item(server, auth_token, target_user, template, category, data, data_file):
	target_type, target_id = target_user
	if data is None: data = data_file.read()
	try:
		result = client.add_item(
			server_base_url=server, 
			auth_token=auth_token, 
			target_type=target_type, 
			target_id=target_id, 
			category=category,
			data_plaintext=data,
			template_id=template)
		click.echo(result)
	except Exception as e:
		click.echo(e)


@cli.command(help="Encrypt and add multiple items from a file")
@global_options()
@click.option('-x', '--send', required=False, default=False, is_flag=True, help='Send to the server rather then logging')
@click.option('-y', '--target-type-field', required=False, default='target_type', help='Field containing target type')
@click.option('-i', '--target-id-field', required=False, default='target_id', help='Field containing target user ID')
@click.option('-c', '--category-field', required=False, default='content', help='Field containing item category')
@click.option('-t', '--template-field', required=False, default=None, help='File containing content template ID')
@click.option('--target-type', required=False, default=None, help='Set/override target type for all items')
@click.option('--target-id', required=False, default=None, help='Set/override target user ID for all items')
@click.option('--category', required=False, default=None, help='Set/override category for all items')
@click.option('--template', required=False, default=None, help='Set/override template for all items')
@click.option('--csv', required=False, default=False, is_flag=True, help='Process file in CSV format rather than JSON')
@click.option('-g', '--global-data', required=False, default=[], nargs=2, multiple=True, help="Inject data all items, e.g. -g key value")
@click.argument('items_file', type=click.File('r'), required=True, default=sys.stdin)
def import_items(
		server, 
		auth_token, 
		target_type_field, 
		target_id_field, 
		category_field,
		template_field, 
		target_type, 
		target_id, 
		category,
		template,
		csv,
		global_data,
		items_file,
		send):
	global_data = { k: v for k, v in global_data }
	if csv:
		items = list(csv_lib.DictReader(items_file))
	else:
		items = json.load(items_file)
	try:
		client.add_items(
			server_base_url=server, 
			auth_token=auth_token,
			target_type_field=target_type_field,
			target_id_field=target_id_field,
			category_field=category_field,
			template_id_field=template_field,
			override_target_type=target_type, 
			override_target_id=target_id,
			override_category=category,
			override_template_id=template,
			global_data=global_data,
			items=items,
			dry_run=not send,
			log_fn=click.echo)
	except Exception as e:
		click.echo(repr(e))


if __name__ == '__main__':
	cli(auto_envvar_prefix='TB', obj={})
