from types import MappingProxyType
from typing import cast

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from statsmodels import api as sm
from statsmodels.tsa.seasonal import seasonal_decompose, STL

from mundi import region
from pydemic.fitting import diff
from pydemic.plot import mark_x, color
from pydemic.region import RegionT
from pydemic.types import ValueStd
from pydemic.utils import coalesce
from pydemic_ui import st

id_ = lambda x: x


def cross_validation(data, fn, initial=None, period=None, horizon=None) -> pd.DataFrame:
    """

    Args:
        data:
        fn:
        initial:
        period:
        horizon:

    Returns:

    """
    validator = Validator(initial=initial, period=period, horizon=horizon, predictor=fn)
    validator.fit(data)
    return validator.cross_validation()


class Validator:
    def __init__(self, period, initial=None, horizon=None, predictor=None):
        self.period = period
        self.initial = coalesce(initial, 2 * period)
        self.horizon = coalesce(horizon, 2 * period)
        self.predictor = predictor

    def fit(self, X):
        ...

    def forecast(self, training_data, periods) -> pd.DataFrame:
        ...

    def cross_validation(self) -> pd.DataFrame:
        ...


plt.gcf()

# r: RegionT = region("BR-SP")
# r: RegionT = region("ES")
r: RegionT = region("BR-SP")

cases = r.pydemic.epidemic_curve()["cases"]
m = STLTrend("multiplicative")
m.fit(diff(cases))
m.plot_components(grid=True, logy=True)
st.pyplot()

forecast = m.predict(60)
m.plot(forecast, logy=True, grid=True)
st.pyplot()
