import click
import sys
import json

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


@cli.command(help='Encrypt input to the server\'s public key')
@global_options(auth_token=False)
@click.argument('plaintext_file', type=click.File('rb'), required=False, default=sys.stdin)
def encrypt(server, plaintext, plaintext_file):
	public_key = client.get_public_key(server)
	if plaintext is None: plaintext = plaintext_file.read()
	ciphertext = client.encrypt(plaintext=plaintext, public_key_b58=public_key)
	return ciphertext


@cli.command(help="Encrypt and add an item for a given user ID")
@global_options()
@click.option('-t', '--target', nargs=2, type=str, required=True, help='Target, e.g.: --target twitter 44196397')
@click.option('-p', '--plaintext', required=False, default=None)
@click.argument('plaintext_file', type=click.File('rb'), required=False, default=sys.stdin)
def add(server, auth_token, target, plaintext, plaintext_file):
	target_type, target_id = target
	if plaintext is None: plaintext = plaintext_file.read()
	result = client.add_item(
		server_base_url=server, 
		target_type=target_type, 
		target_id=target_id, 
		auth_token=auth_token, 
		item_plaintext=plaintext)
	click.echo(result)


@cli.command(help="Encrypt and add multiple items from a file")
@global_options()
@click.option('-d', '--dry-run', required=False, default=False, is_flag=True, help='Print what would be sent to the server')
@click.option('-t', '--target-type-field', required=False, default='target_type', help='Field containing target type')
@click.option('-i', '--target-id-field', required=False, default='target_id', help='Field containing target user ID')
@click.option('-c', '--content-field', required=False, default='content', help='Field containing target user ID')
@click.option('-f', '--template-file', required=False, default=None, help='File containing content template')
@click.option('--target-type', required=False, default=None, help='Override target type for all items')
@click.option('--target-id', required=False, default=None, help='Override target user ID for all items')
@click.argument('items_file', type=click.File('rb'), required=False, default=sys.stdin)
def add_all(
		server, 
		auth_token, 
		target_type_field, 
		target_id_field, 
		content_field,
		template_file, 
		target_type, 
		target_id, 
		items_file,
		dry_run):
	items = json.load(items_file)
	result = client.add_items(
		server_base_url=server, 
		auth_token=auth_token, 
		items=items,
		content_field=content_field,
		template_file=template_file,
		target_type_field=target_type_field,
		target_id_field=target_id_field,
		override_target_type=target_type, 
		override_target_id=target_id,
		dry_run=dry_run,
		log_fn=click.echo)
	click.echo(result)


if __name__ == '__main__':
	cli(auto_envvar_prefix='TB', obj={})
