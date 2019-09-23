import numpy as np
import pytest

from sktime.transformers.forecasting import Deseasonaliser
from sktime.utils.testing import generate_seasonal_time_series_data_with_trend, generate_time_series_data_with_trend
from sktime.utils.data_container import select_times, tabularise


@pytest.mark.parametrize("n_samples", [1, 10])
@pytest.mark.parametrize("order", [0, 1, 2])
@pytest.mark.parametrize("model", ['additive', 'multiplicative'])
@pytest.mark.parametrize("sp", [1, 4, 12, 24])
def test_transform_inverse_transform_equivalence(n_samples, order, sp, model):
    # generate data
    n_obs = 100
    X = generate_seasonal_time_series_data_with_trend(n_samples=n_samples, n_obs=n_obs, order=order, sp=sp, model=model)

    # split data for testing
    cutoff = n_obs - (n_obs // 4)
    a_times = np.arange(n_obs)[:cutoff]
    b_times = np.arange(n_obs)[cutoff:]

    A = select_times(X, a_times)
    B = select_times(X, b_times)

    # test successful deseasonalising when true seasonal periodicity is given
    tran = Deseasonaliser(sp=sp, model=model)
    At = tran.fit_transform(A)
    assert At.shape == A.shape
    assert tabularise(At).shape == tabularise(At).shape

    # compare deseasonalised data with data generated by same process only without seasonality
    expected = generate_time_series_data_with_trend(n_instances=n_samples, n_timepoints=cutoff, order=order)

    # adjust testing criteria for complexity of data/model
    if model == 'multiplicative' and (order > 0):
        np.testing.assert_allclose(tabularise(At).values, tabularise(expected).values, rtol=0.06)
    else:
        np.testing.assert_array_almost_equal(tabularise(At).values, tabularise(expected).values, decimal=1)

    # test that inverse transform on same data restores original data
    Ait = tran.inverse_transform(At)
    assert Ait.shape == A.shape
    assert tabularise(Ait).shape == tabularise(A).shape
    np.testing.assert_array_almost_equal(Ait.iloc[0, 0].values, A.iloc[0, 0].values)

    # test correct inverse transform on new data with a different time index
    # e.g. necessary for inverse transforms after predicting/forecasting
    C = generate_time_series_data_with_trend(n_instances=n_samples, n_timepoints=n_obs, order=order)
    C = select_times(C, b_times)
    Cit = tran.inverse_transform(C)
    if model == 'multiplicative' and (order > 0):
        np.testing.assert_allclose(B.iloc[0, 0].values, Cit.iloc[0, 0].values, rtol=0.15)
    else:
        np.testing.assert_array_almost_equal(B.iloc[0, 0].values, Cit.iloc[0, 0].values, decimal=1)


@pytest.mark.parametrize("model", ['additive', 'multiplicative'])
def test_zero_sp_identity(model):
    # test if zero seasonal periodicity returns unchanged X (identity transformer)
    n_obs = 100
    n_samples = 10
    order = 1
    sp = 1
    X = generate_seasonal_time_series_data_with_trend(n_samples=n_samples, n_obs=n_obs, order=order, sp=sp, model=model)

    tran = Deseasonaliser(sp=sp, model=model)
    Xt = tran.fit_transform(X)
    np.testing.assert_array_almost_equal(tabularise(Xt).values, tabularise(X).values)

    # test that inverse transform on same data restores original data
    Xit = tran.inverse_transform(Xt)
    np.testing.assert_array_almost_equal(tabularise(Xit).values, tabularise(X).values)


@pytest.mark.parametrize("sp", [4, 12, 24])
def test_align_seasonal_components_to_new_index(sp):
    # test if for a new time index seasonal components are aligned properly
    n_obs = 100
    X = generate_seasonal_time_series_data_with_trend(n_samples=1, n_obs=n_obs, sp=sp)

    tran = Deseasonaliser(sp=sp)
    tran.fit_transform(X)

    new_index = np.arange(n_obs, n_obs * 2)

    actual = tran._align_seasonal_components_to_index(new_index)

    # alternative way to align seasonal components to new index, but slower, hence only used here for testing
    expected = np.atleast_2d(np.resize(tran.seasonal_components_, new_index[-1] + 1)[new_index[0]:new_index[0] + sp])

    np.testing.assert_array_equal(actual, expected)
