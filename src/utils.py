import hashlib

def check_password_hash_md5(password, hash):
  if hash == hashlib.md5(password.encode()).hexdigest():
    return True
  else:
    return False
