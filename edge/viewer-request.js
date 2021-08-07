function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // If URI ends with /, forward to origin's index.html at that URI
  if (uri.endsWith('/')) {
    request.uri += 'index.html';
  } else if (uri.endsWith('/index.html')) {
    // If URI filename is index.html, redirect to remove index.html
    return {
      statusCode: 301,
      statusDescription: 'Found',
      headers: {
        'location': {
          value: uri.slice(0, uri.lastIndexOf('index.html')),
        },
      },
    };
  } else {
    var filename = uri.split('/').slice(-1).pop();
    if (!filename.includes('.')) {
      // If URI doesn't end with / and URI has no ., redirect to canonical
      // /-terminated URI
      return {
        statusCode: 301,
        statusDescription: 'Found',
        headers: {
          'location': {
            value: uri + '/',
          },
        },
      };
    }
  }

  return request;
}
