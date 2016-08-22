import json
from urllib.parse import quote_plus
from jwkest.jwk import rsa_load, RSAKey
from jwkest.jws import JWS
from jwkest.jwt import JWT

if __name__ == "__main__":
    _bkey = rsa_load("test.key")
    sign_key = RSAKey().load_key(_bkey)
    sign_key.use = "sig"
    algorithm = "RS256"
    data = {
        "redirect_endpoint": "http://www.google.se",
        "id": "qwerty",
        "attr": {"attr1": ["Attribute 1:1", "Attribute 1:2"],
                 "attr2": ["Attribute 2"],
                 "attr3": ["Attribute 3"]}
    }
    _jws = JWS(json.dumps(data), alg=algorithm)
    _jws = _jws.sign_compact([sign_key])
    tmp_jwt = JWT().unpack(_jws)
    jso = tmp_jwt.payload()
    print(quote_plus(_jws))
