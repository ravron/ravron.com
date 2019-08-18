#!/usr/bin/env zsh

set -eux

setopt extendedglob

rm -r public/^CNAME
hugo --minify
git -C public add .
git -C public commit -m 'Update site'
git -C public push

git add public
git commit -m 'Bump public'
git push
