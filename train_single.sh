#!/usr/bin/env bash

export CUDA_VISIBLE_DEVICES=0

for site in NYU UM USM
do
  for split in 0 1 2 3 4
  do
    python single.py --site $site --split $split
  done
done