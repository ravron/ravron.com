function handler(event) {
  return {
    statusCode: 301,
    statusDescription: 'Found',
    headers: {
      'location': {
        value: 'https://ravron.com' + event.request.uri,
      },
    },
  };
}
