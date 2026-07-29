"""src/intelligence/routing/__init__.py"""
from src.intelligence.routing.routing_rules import resolve_route, PRIMARY_ROUTING_TABLE
from src.intelligence.routing.router import SignalRouter, RouteDecision

__all__ = ["SignalRouter", "RouteDecision", "resolve_route", "PRIMARY_ROUTING_TABLE"]
