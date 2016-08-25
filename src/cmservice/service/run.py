from cmservice.service.wsgi import create_app

app = create_app()

if __name__ == '__main__':
    import ssl

    context = None
    if app.config['SSL']:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain(app.config['SERVER_CERT'], app.config['SERVER_KEY'])

    print('CMservice running at %s:%s' % (app.config['HOST'], app.config['PORT']))
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'],
            ssl_context=context)
