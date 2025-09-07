local t = import 'kube-thanos/thanos.libsonnet';

// For an example with every option and component, please check all.jsonnet

local commonConfig = {
  config+:: {
    local cfg = self,
    namespace: 'thanos',
    version: 'v0.39.2',
    image: 'quay.io/thanos/thanos:' + cfg.version,
    imagePullPolicy: 'IfNotPresent',
    objectStorageConfig: {
      name: 'thanos-objectstorage',
      key: 'thanos.yaml',
    },
    hashringConfigMapName: 'hashring-config',
    volumeClaimTemplate: {
      spec: {
        accessModes: ['ReadWriteOnce'],
        resources: {
          requests: {
            storage: '10Gi',
          },
        },
      },
    },
  },
};

local cs = t.compactShards(commonConfig.config {
  shards: 3,
  sourceLabels: ['cluster'],
  replicas: 1,
  serviceMonitor: true,
  disableDownsampling: true,
});


local b = t.bucket(commonConfig.config {
  replicas: 1,
  label: 'cluster_name',
  refresh: '5m',
  // Example on how to overwrite the tracing config on a per component basis
  // tracing+: {
  //   config+: {
  //     service_name: 'awesome-thanos-bucket',
  //   },
  // },
});

local i = t.receiveIngestor(commonConfig.config {
  replicas: 3,
  replicaLabels: ['receive_replica'],
  replicationFactor: 3,
  // Disable shipping to object storage for the purposes of this example
  objectStorageConfig: null,
  serviceMonitor: true,
});

local r = t.receiveRouter(commonConfig.config {
  replicas: 3,
  replicaLabels: ['receive_replica'],
  replicationFactor: 3,
  // Disable shipping to object storage for the purposes of this example
  objectStorageConfig: null,
  endpoints: i.endpoints,
});

local s = t.store(commonConfig.config {
  replicas: 1,
  serviceMonitor: true,
});

local q = t.query(commonConfig.config {
  replicas: 1,
  replicaLabels: ['prometheus_replica', 'rule_replica'],
  serviceMonitor: true,
  stores: [s.storeEndpoint] + i.storeEndpoints,
});


{ ['thanos-bucket-' + name]: b[name] for name in std.objectFields(b) if b[name] != null } +
{
  ['thanos-compact-' + shard + '-' + name]: cs.shards[shard][name]
  for shard in std.objectFields(cs.shards)
  for name in std.objectFields(cs.shards[shard])
  if cs.shards[shard][name] != null
} +
{ ['thanos-store-' + name]: s[name] for name in std.objectFields(s) } +
{ ['thanos-query-' + name]: q[name] for name in std.objectFields(q) } +
{ ['thanos-receive-router-' + resource]: r[resource] for resource in std.objectFields(r) } +
{ ['thanos-receive-ingestor-' + resource]: i[resource] for resource in std.objectFields(i) if resource != 'ingestors' } +
{
  ['thanos-receive-ingestor-' + hashring + '-' + resource]: i.ingestors[hashring][resource]
  for hashring in std.objectFields(i.ingestors)
  for resource in std.objectFields(i.ingestors[hashring])
  if i.ingestors[hashring][resource] != null
}