from .base import REGISTRY, Param, PlotType, register

# 各グラフ種類を import して REGISTRY に登録する
from . import timeseries  # noqa: F401

__all__ = ["REGISTRY", "Param", "PlotType", "register"]
