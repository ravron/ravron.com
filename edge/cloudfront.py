CSP_VALUE = ' '.join([
     "default-src 'none';",
     "img-src 'self';",
     "style-src 'self';",
     "block-all-mixed-content;",
     "require-sri-for script style;",
     "frame-ancestors 'none';",
     "base-uri 'none';",
     "form-action 'none';",
    ])


def lambda_handler(event, context):
    response = event['Records'][0]['cf']['response']
    headers = response['headers']

    headers['content-security-policy'] = [{
        'value': CSP_VALUE,
        }]

    headers['x-content-type-options'] = [{
        'value': 'nosniff',
        }]

    headers['referrer-policy'] = [{
        'value': 'same-origin',
        }]

    headers['strict-transport-security'] = [{
        'value': 'max-age=63072000; includeSubDomains; preload',
        }]

    return response
