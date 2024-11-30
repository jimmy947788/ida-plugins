#!/bin/bash

echo "==== download python 3.11 ===="
wget https://www.python.org/ftp/python/3.11.10/Python-3.11.10.tgz
tar -xvf Python-3.11.10.tgz


echo "==== build python 3.11 ===="
cd Python-3.11.10
./configure --enable-optimizations \
    --enable-shared  # 要生成共享库才有libpython3.11.so
# --prefix=$IDAUSR/python311 \

make -j$(nproc)
make install

echo "==== check libpython3.11.so ===="
ls /usr/local/lib/ | grep libpython3.11.so


echo "==== set python 3.11 ===="
export PYTHONPATH="$IDADIR/python:$PYTHONPATH"
# find libpython3.11.so path , for pip use success
# ind /usr/local -name "libpython3.11.so.1.0"
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH


echo "==== IDA pro Switch python 3.11 ===="
cd $IDADIR
./idapyswitch --force-path /usr/local/lib/libpython3.11.so.1.0


echo "==== install pip ===="
pip3.11 install --upgrade pip
pip3.11 install z3-solver