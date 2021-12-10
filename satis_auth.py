import time

from eth_account.messages import encode_defunct
from requests.auth import AuthBase
from web3.auto import w3


class SatisAuth(AuthBase):
    def __init__(self, key):
        self.key = key

    def __call__(self, request):
        timestamp = str(int(time.time()))
        url = request.path_url
        body = request.body.decode() if request.body else ""
        message = encode_defunct(text=timestamp + request.method + url + body)
        signature = w3.eth.account.sign_message(message, private_key=self.key).signature.hex()

        request.headers.update({
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        })
        return request
