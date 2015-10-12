import json
from urllib.parse import quote_plus
from jwkest.jwk import rsa_load, RSAKey
from jwkest.jws import JWS

__author__ = 'haho0032'

if __name__ == "__main__":
    _bkey = rsa_load("test.key")
    sign_key = RSAKey().load_key(_bkey)
    sign_key.use = "sig"
    algorithm = "RS256"
    data = {
        "redirect_endpoint": "http://www.google.se",
        "id": "qwerty",
        "attr": ["attr1", "attr2", "attr3"]
    }
    _jws = JWS(json.dumps(data), alg=algorithm)
    print(quote_plus(_jws.sign_compact([sign_key])))
