\"\"\"Security bouncer module with is_safe function.\"\"\"

SAFE_WHITELIST = [
    'grep',
    'ls',
    'cat',
    'echo',
    'find',
    'pwd',
    'mkdir',
    'rmdir',
    'cp',
    'mv',
    'chmod',
    'chown',
    'tar',
    'gzip',
    'gunzip',
]

def is_safe(command: str) -> bool:
    """
    Return True if the command is considered safe, False otherwise.
    Safety is determined by checking if the command (whole string) is in the SAFE_WHITELIST.
    """
    return command in SAFE_WHITELIST