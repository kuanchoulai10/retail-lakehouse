# Thanos Deployment

## K8S

There are 3 ways of deploying Thanos on Kubernetes:

- [Community Helm charts](https://artifacthub.io/packages/search?ts_query_web=thanos)
- [prometheus-operator](https://github.com/coreos/prometheus-operator)
- [kube-thanos](https://github.com/thanos-io/kube-thanos): Jsonnet based Kubernetes templates.

We use **Bitnami Thanos Helm chart** to deploy Thanos components.


有遇到個問題是，ruler執行時，遇到too many open files的問題，問題是minikube 裡的fs.inotify.max_user_instances 預設是128，太小了

```bash
minikube -p retail-lakehouse ssh
docker@retail-lakehouse:~$ sysctl fs.inotify.max_user_watches
fs.inotify.max_user_watches = 1048576
docker@retail-lakehouse:~$ sysctl fs.inotify.max_user_instances
fs.inotify.max_user_instances = 128
docker@retail-lakehouse:~$ cat /proc/sys/fs/file-max
9223372036854775807
```

調高到1024
```
sudo sysctl -w fs.inotify.max_user_instances=1024
```

## References

- [Community Thanos Kubernetes Applications | Thanos Docs](https://thanos.io/tip/thanos/getting-started.md/#community-thanos-kubernetes-applications) 