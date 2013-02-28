HEX = frozenset('abcdef0123456789')

def is_hex(s):
	return set(s) < HEX