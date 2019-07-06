#!/usr/bin/env bash

set -eux

# Need extglob for !(...) syntax
shopt -s extglob

rm -r public/!(CNAME)
hugo --minify
git -C public add .
git -C public commit -m 'Update site'
git -C public push

