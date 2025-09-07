local t = import 'kube-thanos/thanos.libsonnet';

// For an example with every option and component, please check all.jsonnet
// --8<-- [start:common-config]
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
// --8<-- [end:common-config]


// --8<-- [start:receiver]
local ri = t.receiveIngestor(commonConfig.config {
  replicas: 3,
  replicationFactor: 3,
  replicaLabels: ['receive_replica'],
  serviceMonitor: true,
});

local rr = t.receiveRouter(commonConfig.config {
  routerReplicas: 3,
  replicationFactor: 3,
  replicaLabels: ['receive_replica'],
  // Disable shipping to object storage for the purposes of this example
  objectStorageConfig: null,
  endpoints: ri.endpoints,
});
// --8<-- [end:receiver]


// --8<-- [start:store-gateway]
local strs = t.storeShards(commonConfig.config {
  shards: 3,
  replicas: 1,
  serviceMonitor: true,
  bucketCache: {
    type: 'memcached',
    config+: {
      // NOTICE: <MEMCACHED_SERVICE> is a placeholder to generate examples.
      // List of memcached addresses, that will get resolved with the DNS service discovery provider.
      // For DNS service discovery reference https://thanos.io/tip/thanos/service-discovery.md/#dns-service-discovery
      // addresses: ['dnssrv+_client._tcp.<MEMCACHED_SERVICE>.%s.svc.cluster.local' % commonConfig.config.namespace],
      addresses: ['dnssrv+_client._tcp.memcached.%s.svc.cluster.local' % commonConfig.config.namespace],
    },
  },
  indexCache: {
    type: 'memcached',
    config+: {
      // NOTICE: <MEMCACHED_SERVICE> is a placeholder to generate examples.
      // List of memcached addresses, that will get resolved with the DNS service discovery provider.
      // For DNS service discovery reference https://thanos.io/tip/thanos/service-discovery.md/#dns-service-discovery
      addresses: ['dnssrv+_client._tcp.memcached.%s.svc.cluster.local' % commonConfig.config.namespace],
    },
  },
});
// --8<-- [end:store-gateway]


// --8<-- [start:compactor]
local cs = t.compactShards(commonConfig.config {
  shards: 3,
  sourceLabels: ['cluster'],
  replicas: 1,
  serviceMonitor: true,
  disableDownsampling: true,
});
// --8<-- [end:compactor]


// --8<-- [start:query]
local q = t.query(commonConfig.config {
  replicas: 3,
  replicaLabels: ['prometheus_replica', 'rule_replica', 'receive_replica'],
  serviceMonitor: true,
  stores: ri.storeEndpoints + [
    'dnssrv+_grpc._tcp.%s.%s.svc.cluster.local' % [service.metadata.name, service.metadata.namespace]
    for service in [strs.shards[shard].service for shard in std.objectFields(strs.shards)]
  ],
});

local qf = t.queryFrontend(commonConfig.config {
  replicas: 3,
  downstreamURL: 'http://%s.%s.svc.cluster.local:%d' % [
    q.service.metadata.name,
    q.service.metadata.namespace,
    q.service.spec.ports[1].port,
  ],
  splitInterval: '12h',
  maxRetries: 10,
  logQueriesLongerThan: '10s',
  serviceMonitor: true,
  queryRangeCache: {
    type: 'memcached',
    config+: {
      // NOTICE: <MEMCACHED_SERVICE> is a placeholder to generate examples.
      // List of memcached addresses, that will get resolved with the DNS service discovery provider.
      // For DNS service discovery reference https://thanos.io/tip/thanos/service-discovery.md/#dns-service-discovery
      // addresses: ['dnssrv+_client._tcp.<MEMCACHED_SERVICE>.%s.svc.cluster.local' % commonConfig.namespace],
      addresses: ['dnssrv+_client._tcp.memcached.%s.svc.cluster.local' % commonConfig.config.namespace],
    },
  },
  labelsCache: {
    type: 'memcached',
    config+: {
      // NOTICE: <MEMCACHED_SERVICE> is a placeholder to generate examples.
      // List of memcached addresses, that will get resolved with the DNS service discovery provider.
      // For DNS service discovery reference https://thanos.io/tip/thanos/service-discovery.md/#dns-service-discovery
      // addresses: ['dnssrv+_client._tcp.<MEMCACHED_SERVICE>.%s.svc.cluster.local' % commonConfig.namespace],
      addresses: ['dnssrv+_client._tcp.memcached.%s.svc.cluster.local' % commonConfig.config.namespace],
    },
  },
});
// --8<-- [end:query]


// --8<-- [start:bucket-web-ui]
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
// --8<-- [end:bucket-web-ui]


// --8<-- [start:objects]
{ ['thanos-receive-router-' + resource]: rr[resource] for resource in std.objectFields(rr) } +
{ ['thanos-receive-ingestor-' + resource]: ri[resource] for resource in std.objectFields(ri) if resource != 'ingestors' } +
{
  ['thanos-receive-ingestor-' + hashring + '-' + resource]: ri.ingestors[hashring][resource]
  for hashring in std.objectFields(ri.ingestors)
  for resource in std.objectFields(ri.ingestors[hashring])
  if ri.ingestors[hashring][resource] != null
} +
{
  ['thanos-store-' + shard + '-' + name]: strs.shards[shard][name]
  for shard in std.objectFields(strs.shards)
  for name in std.objectFields(strs.shards[shard])
  if strs.shards[shard][name] != null
} +
{
  ['thanos-compact-' + shard + '-' + name]: cs.shards[shard][name]
  for shard in std.objectFields(cs.shards)
  for name in std.objectFields(cs.shards[shard])
  if cs.shards[shard][name] != null
} +
{ ['thanos-query-' + name]: q[name] for name in std.objectFields(q) } +
{ ['thanos-query-frontend-' + name]: qf[name] for name in std.objectFields(qf) if qf[name] != null } +
{ ['thanos-bucket-' + name]: b[name] for name in std.objectFields(b) if b[name] != null }
// --8<-- [end:objects]