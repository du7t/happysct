#!/usr/bin/env bash

kubectl diff -k overlays/$1 | grep -q Deployment
ret=$?
kubectl apply -k overlays/$1
if [ $ret -ne 0 ]; then
        echo "Restart"
        kubectl rollout restart deployment/$2
fi