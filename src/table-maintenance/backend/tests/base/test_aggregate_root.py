"""Tests for AggregateRoot base type."""

from dataclasses import dataclass

from base import AggregateRoot, DomainEvent, EntityId


@dataclass(frozen=True)
class OrderId(EntityId):
    pass


@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    order_id: str


@dataclass(eq=False)
class Order(AggregateRoot[OrderId]):
    id: OrderId
    total: int


def test_aggregate_root_is_entity():
    """AggregateRoot should be a subclass of Entity."""
    from base import Entity

    assert issubclass(AggregateRoot, Entity)


def test_no_events_initially():
    order = Order(id=OrderId("1"), total=100)
    assert order.collect_events() == []


def test_register_and_collect_events():
    order = Order(id=OrderId("1"), total=100)
    event = OrderCreated(order_id="1")
    order.register_event(event)
    assert order.collect_events() == [event]


def test_collect_events_clears():
    """collect_events should return events and clear the internal list."""
    order = Order(id=OrderId("1"), total=100)
    order.register_event(OrderCreated(order_id="1"))
    order.collect_events()
    assert order.collect_events() == []


def test_aggregate_root_is_not_a_dataclass():
    """AggregateRoot itself should be a plain class, not a dataclass."""
    import dataclasses

    assert not dataclasses.is_dataclass(AggregateRoot)
