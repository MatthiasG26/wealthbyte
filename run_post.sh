#!/bin/bash
cd /Users/turboclaimmac2/wealthbyte
export $(cat .env | xargs)
python3 post.py >> /Users/turboclaimmac2/wealthbyte/post.log 2>&1
