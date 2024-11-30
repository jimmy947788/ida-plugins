#!/bin/bash

# check envuriment IDAUSR and IDADIR
if [ -z "$IDAUSR" ]; then
    echo "Please set IDAUSR environment variable"
    exit 1
fi

if [ -z "$IDADIR" ]; then
    echo "Please set IDADIR environment variable"
    exit 1
fi


echo "==== install plugins a ===="