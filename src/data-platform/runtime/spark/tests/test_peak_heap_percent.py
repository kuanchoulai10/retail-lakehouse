from __future__ import annotations

from peak_heap_percent import peak_heap_percent

MIB = 1024 * 1024
UI = "http://driver:4040"


class _Conf:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class _Context:
    def __init__(self, ui, conf):
        self.uiWebUrl = ui
        self.applicationId = "spark-0001"
        self._conf = _Conf(conf)

    def getConf(self):
        return self._conf


class _Spark:
    def __init__(self, ui=UI, conf=None):
        self.sparkContext = _Context(
            ui, {"spark.driver.memory": "768m", "spark.executor.memory": "1536m"} if conf is None else conf
        )


def _executor(id_, heap=None):
    entry = {"id": id_}
    if heap is not None:
        entry["peakMemoryMetrics"] = {"JVMHeapMemory": heap}
    return entry


def test_peak_heap_percent_is_the_largest_share_of_driver_and_executors():
    fetched = []

    def fetch(url):
        fetched.append(url)
        return [_executor("driver", 384 * MIB), _executor("1", 1152 * MIB)]

    assert peak_heap_percent(_Spark(), fetch=fetch) == 75
    assert fetched == [f"{UI}/api/v1/applications/spark-0001/allexecutors"]


def test_peak_heap_percent_uses_the_driver_memory_for_the_driver():
    def fetch(_url):
        return [_executor("driver", 700 * MIB), _executor("1", 100 * MIB)]

    assert peak_heap_percent(_Spark(), fetch=fetch) == 91


def test_peak_heap_percent_defaults_to_spark_default_memory():
    def fetch(_url):
        return [_executor("driver", 512 * MIB)]

    assert peak_heap_percent(_Spark(conf={}), fetch=fetch) == 50


def test_peak_heap_percent_is_none_without_metrics():
    assert peak_heap_percent(_Spark(), fetch=lambda _url: [_executor("driver"), _executor("1")]) is None


def test_peak_heap_percent_is_none_when_the_ui_is_off():
    def fetch(_url):
        raise AssertionError("no UI to read")

    assert peak_heap_percent(_Spark(ui=None), fetch=fetch) is None


def test_peak_heap_percent_is_none_when_the_ui_cannot_be_read():
    def fetch(_url):
        raise OSError("connection refused")

    assert peak_heap_percent(_Spark(), fetch=fetch) is None


def test_peak_heap_percent_is_none_for_an_unexpected_reply():
    assert peak_heap_percent(_Spark(), fetch=lambda _url: {"error": "nope"}) is None
