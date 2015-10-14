import json
from urllib.parse import quote_plus
from jwkest.jwk import rsa_load, RSAKey
from jwkest.jws import JWS
from jwkest.jwt import JWT

__author__ = 'haho0032'

if __name__ == "__main__":
    _bkey = rsa_load("test.key")
    sign_key = RSAKey().load_key(_bkey)
    sign_key.use = "sig"
    algorithm = "RS256"
    data = {
        "redirect_endpoint": "http://www.google.se",
        "id": "qwerty",
        "attr": [{"key": "attr1", "value": "Attribute 1"},
                 {"key": "attr2", "value": "Attribute 2"},
                 {"key": "attr3", "value": "Attribute 3"}]
    }
    _jws = JWS(json.dumps(data), alg=algorithm)
    _jws = _jws.sign_compact([sign_key])
    tmp_jwt = JWT().unpack(_jws)
    jso = tmp_jwt.payload()
    print(quote_plus(_jws))
