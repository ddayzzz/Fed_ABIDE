#!/usr/bin/env bash
export CUDA_VISIBLE_DEVICES=5

for split in 0
do
  outfile=${PWD}/log/feddistill_at_client/split_$split
  mkdir -p $outfile
  python feddistill_at_client.py --split $split > $outfile/output.log 2>&1
done