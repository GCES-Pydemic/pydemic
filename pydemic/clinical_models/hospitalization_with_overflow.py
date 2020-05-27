import numpy as np
import pandas as pd
import sidekick as sk
from scipy.integrate import cumtrapz
from sidekick import placeholder as _

from .hospitalization_with_delay import HospitalizationWithDelay
from ..utils import param_property, sliced


class HospitalizationWithOverflow(HospitalizationWithDelay):
    """
    Hospitals have a maximum number of ICU and regular clinical beds.
    Death rates increase when this number overflows.
    """

    hospitalization_overflow_bias = param_property(default=0.0)
    icu_capacity = param_property()
    hospital_capacity = param_property()
    icu_occupancy = param_property(default=0.75)
    hospital_occupancy = param_property(default=0.75)

    icu_surge_capacity = sk.property(_.icu_capacity * (1 - _.icu_occupancy))
    hospital_surge_capacity = sk.property(_.hospital_capacity * (1 - _.hospital_occupancy))

    def __init__(self, *args, occupancy=None, **kwargs):
        if occupancy is not None:
            kwargs.setdefault("icu_occupancy", occupancy)
            kwargs.setdefault("hospital_occupancy", occupancy)
        super().__init__(*args, **kwargs)

    def _icu_capacity(self):
        if self.region is not None:
            return self.region.icu_capacity
        return 0.0

    def _hospital_capacity(self):
        if self.region is not None:
            return self.region.hospital_capacity
        return 0.0

    #
    # Data methods
    #

    # Deaths
    def get_data_deaths(self, idx):
        return self["natural_deaths", idx] + self["overflow_deaths", idx]

    def get_data_natural_deaths(self, idx):
        """
        The number of deaths assuming healthcare system in full capacity.
        """
        return super().get_data_deaths(idx)

    def get_data_overflow_deaths(self, idx):
        """
        The number of deaths caused by overflowing the healthcare system.
        """
        return self["icu_overflow_deaths", idx] + self["hospital_overflow_deaths", idx]

    def get_data_icu_overflow_deaths(self, idx):
        """
        The number of deaths caused by overflowing ICUs.
        """
        # We just want to comput the excess deaths, so we discount the
        # contribution from natural ICUFR that is computed in natural deaths
        times = sliced(self.times, idx)
        scale = 1 - self.ICUFR
        area = cumtrapz(self["critical_overflow", idx] * scale, times, initial=0)
        return pd.Series(area / self.icu_period, index=times)

    def get_data_hospital_overflow_deaths(self, idx):
        """
        The number of deaths caused by overflowing regular hospital beds.
        """
        times = sliced(self.times, idx)
        area = cumtrapz(self["severe_overflow", idx], times, initial=0)
        cases = area / self.hospitalization_period
        ratio = (self.Qcr / self.Qsv) * self.hospitalization_overflow_bias
        deaths = cases * min(ratio, 1)
        return pd.Series(deaths, index=times)

    def get_data_overflow_death_rate(self, idx):
        """
        Daily number of additional deaths due to overflowing the healthcare system.
        """
        return self["overflow_deaths", idx].diff().fillna(0)

    def get_data_icu_overflow_death_rate(self, idx):
        """
        Daily number of additional deaths due to overflowing the ICU capacity.
        """
        return self["icu_overflow_deaths", idx].diff().fillna(0)

    def get_data_hospital_overflow_death_rate(self, idx):
        """
        Daily number of additional deaths due to overflowing hospital capacity.
        """
        return self["hospital_overflow_deaths", idx].diff().fillna(0)

    # Severe/hospitalizations dynamics
    def get_data_severe_overflow(self, idx):
        """
        The number of severe cases that are not being treated in a hospital
        facility.
        """
        data = np.maximum(self["severe", idx] - self.hospital_surge_capacity, 0)
        return pd.Series(data, index=sliced(self.times, idx))

    def get_data_hospitalized_cases(self, idx):
        times = sliced(self.times, idx)
        area = cumtrapz(self["hospitalized", idx], times, initial=0)
        return pd.Series(area / self.hospitalization_period, index=times)

    def get_data_hospitalized(self, idx):
        demand = self["severe", idx]
        data = np.minimum(demand, self.hospital_surge_capacity)
        return pd.Series(data, index=sliced(self.times, idx))

    # Critical/ICU dynamics
    def get_data_critical_overflow(self, idx):
        """
        The number of critical cases that are not being treated in an ICU
        facility.
        """
        data = np.maximum(self["critical", idx] - self.icu_surge_capacity, 0)
        return pd.Series(data, index=sliced(self.times, idx))

    def get_data_icu_cases(self, idx):
        times = sliced(self.times, idx)
        area = cumtrapz(self["icu", idx], times, initial=0)
        return pd.Series(area / self.icu_period, index=times)

    def get_data_icu(self, idx):
        demand = self["hospitalized", idx]
        data = np.minimum(demand, self.icu_surge_capacity)
        return pd.Series(data, index=sliced(self.times, idx))

    # Aliases
    get_data_icu_overflow = get_data_critical_overflow
    get_data_hospital_overflow = get_data_severe_overflow

    #
    # Results methods
    #
    def get_overflow_date(self, col, value=0.0):
        """
        Get date in which column assumes a value greater than value.
        """
        for date, x in self[f"{col}:dates"].iteritems():
            if x > value:
                return date
        return None

    def get_result_dates__icu_overflow(self):
        return self.get_overflow_date("critical", self.icu_surge_capacity)

    def get_result_dates__hospital_overflow(self):
        return self.get_overflow_date("severe", self.hospital_surge_capacity)