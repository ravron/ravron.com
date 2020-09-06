This repository hosts the source for [ravron.com](https://ravron.com). The site
is built using the static site generator [Hugo](https://gohugo.io/), and hosted
on [S3](https://aws.amazon.com/s3/) using
[CloudFront](https://aws.amazon.com/cloudfront/) as the CDN. Deployment is
handled using [GitHub Actions](https://github.com/features/actions), the source
for which is found in the [.github/workflows directory](.github/workflows).
Security headers are added with
[Lambda@Edge](https://aws.amazon.com/lambda/edge/) using the
[`viewer-response.py`](edge/viewer-response.py) script. If you find any errors or wish to
suggest improvements, pull requests are welcome.
