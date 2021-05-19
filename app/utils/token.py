import time
import itsdangerous
import base64

class Tokens:
    def __init__(self, epoch: int, worker_id: int, process_id: int, secret: str):
        self.epoch = epoch
        self.worker_id = worker_id
        self.process_id = process_id
        self.secret = secret

        self.inc = 0
        self.signer = itsdangerous.TimestampSigner(secret)

    def create_token(self, id: str) -> str:
        based_token = base64.b64encode(id.encode())
        return self.signer.sign(based_token).decode()

    def create_id(self) -> str:
        self.inc += 1
        now = int(time.time() * 1000 - self.epoch)

        snowflake = now << 22
        snowflake |= (self.worker_id) << 17
        snowflake |= (self.process_id) << 12
        snowflake |= self.inc

        return str(snowflake)

    def validate_token(self, token: str, *, max_age: int = None) -> str:
        encoded_token = token.encode()
        data = self.signer.unsign(encoded_token, max_age=max_age)
        if isinstance(data, tuple):
            id = data[0]
        else:
            id = data

        encoded_id = id.decode()
        return base64.b64decode(encoded_id).decode()
