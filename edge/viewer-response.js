var CSP_VALUE = [
  "default-src 'none';",
  "img-src 'self';",
  "style-src 'self';",
  "block-all-mixed-content;",
  "frame-ancestors 'none';",
  "base-uri 'none';",
  "form-action 'none';",
].join(' ')

function handler(event) {
  var headers = event.response.headers;

  headers['content-security-policy'] = {value: CSP_VALUE};

  // Obsoleted by CSP frame-ancestors, but not all browsers honor that
  headers['x-frame-options'] = {value: 'DENY'};

  headers['x-content-type-options'] = {value: 'nosniff'};

  headers['referrer-policy'] = {value: 'same-origin'};

  headers['strict-transport-security'] = {value: 'max-age=63072000; includeSubDomains; preload'};

  return event.response;
}
