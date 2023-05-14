from cryptography.fernet import Fernet


class Secrets:
    @staticmethod
    def generate_key(filepath: str):
        key = Fernet.generate_key()

        with open(filepath, 'wb') as opened_key:
            opened_key.write(key)

    @staticmethod
    def encrypt_save_file(encryption_key: str, original_file: str, encrypted_file: str):
        with open(encryption_key, 'rb') as opened_key:
            key = opened_key.read()
        f = Fernet(key)

        with open(original_file, 'rb') as og_file:
            original = og_file.read()

        encrypted = f.encrypt(original)

        with open(encrypted_file, 'wb') as ec_file:
            ec_file.write(encrypted)

    @staticmethod
    def decrypt_save_file(encryption_key: str, encrypted_file: str, decrypted_file: str):
        with open(encryption_key, 'rb') as opened_key:
            key = opened_key.read()
        f = Fernet(key)

        with open(encrypted_file, 'rb') as ec_file:
            encrypted = ec_file.read()

        decrypted = f.decrypt(encrypted)

        with open(decrypted_file, 'wb') as dc_file:
            dc_file.write(decrypted)

    @staticmethod
    def decrypt_file(encryption_key: str, encrypted_file: str):
        with open(encryption_key, 'rb') as mykey:
            key = mykey.read()
        f = Fernet(key)

        with open(encrypted_file, 'rb') as ec_file:
            encrypted = ec_file.read()

        return f.decrypt(encrypted)
