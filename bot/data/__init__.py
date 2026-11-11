from .base import DataProvider, Headline, Quote


def make_provider(name: str, **kwargs) -> DataProvider:
    name = (name or "stub").lower()
    if name == "stub":
        from .stub import StubProvider
        return StubProvider()
    if name == "ibkr":
        from .ibkr import IBKRProvider
        return IBKRProvider(**kwargs)
    raise ValueError(f"Unknown DATA_PROVIDER {name!r}")


__all__ = ["DataProvider", "Headline", "Quote", "make_provider"]
