# Runbook
Explaining auto quarantine steps and auto replacing a node.

## 1. Auto Quarantine Steps

- Get pod name:
```
NS=default
sudo kubectl -n $NS get pods
```
- Change the label:
```
POD_NAME=podname
sudo kubectl label pod $POD_NAME -n $NS app=debug
```
- Show logs:
```
sudo kubectl logs $POD_NAME -n $NS
```
- Execute shell inside pod and do further debugging:
```
sudo kubectl exec -it $POD_NAME -n $NS -- /bin/sh
```

- Finally, either replace pod's original label or delete the pod.
 
 ## 2. Auto Replace a Node

- Get node name:
```
sudo kubectl get nodes
```
- Mark the node as unschedulable:
```
NODE_NAME=nodename
sudo kubectl cordon $NODE_NAME
```

- Drain the node:
```
sudo kubectl drain $NODE_NAME --ignore-daemonsets
```

- Delete the node:
```
sudo kubectl delete $NODE_NAME
```

- Reset kubeadm state (if using kubeadm):
```
sudo kubeadm reset
```
- On the new node (if using kubeadm):
```
sudo kubeadm token create --print-join-command
```

- Join using the command printed by running the command above.