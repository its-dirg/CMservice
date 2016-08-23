from jwkest.jwk import rsa_load, RSAKey

from cmservice.service.wsgi import create_app

app = create_app()

if __name__ == '__main__':
    import ssl

    context = None
    if app.config['SSL']:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain(app.config['SERVER_CERT'], app.config['SERVER_KEY'])
    keys = []
    for key in app.config['JWT_PUB_KEY']:
        _bkey = rsa_load(key)
        pub_key = RSAKey().load_key(_bkey)
        keys.append(pub_key)
    global cm

    print('CMservice running at %s:%s' % (app.config['HOST'], app.config['PORT']))

    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'],
            ssl_context=context)
