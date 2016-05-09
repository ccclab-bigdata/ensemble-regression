from __future__ import print_function
import __builtin__

import time

from sklearn import linear_model
from sklearn.base import RegressorMixin, MetaEstimatorMixin, BaseEstimator
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor, BaggingRegressor
from sklearn.metrics import mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.svm import SVR, LinearSVR
from sklearn.tree import DecisionTreeRegressor
from theano.gradient import np

from nn_regression import MLPRegressor
from nw_kernel_regression import KernelRegression


class EnsembleRegressor(BaseEstimator, MetaEstimatorMixin, RegressorMixin):
    def __init__(self, verbose=False):
        self._verbose = verbose

        self._regressors_auto = (
            linear_model.LinearRegression(fit_intercept=True),
            Pipeline(
                [('poly', PolynomialFeatures(degree=2)),
                 ('linear', linear_model.LinearRegression(fit_intercept=False))]
            ),
            KernelRegression(kernel='poly'),
            DecisionTreeRegressor(max_depth=4),
            DecisionTreeRegressor(max_depth=None),
            RandomForestRegressor(n_estimators=100),
        )

        self._possible_regressors = (
            linear_model.LinearRegression(fit_intercept=True),
            Pipeline(
                [('poly', PolynomialFeatures(degree=2)),
                 ('linear', linear_model.LinearRegression(fit_intercept=False))]
            ),
            # # linear_model.Ridge(alpha=4, fit_intercept=True),
            KernelRegression(kernel='poly'),
            # linear_model.RidgeCV(alphas=[.01, .1, .3, .5, 1], fit_intercept=True),
            # # linear_model.Lasso(alpha=4, fit_intercept=True),
            # linear_model.LassoCV(n_alphas=100, fit_intercept=True, max_iter=5000),
            # linear_model.ElasticNet(alpha=1),
            # linear_model.ElasticNetCV(n_alphas=100, l1_ratio=.5),
            # linear_model.OrthogonalMatchingPursuit(),
            # linear_model.BayesianRidge(),
            # # linear_model.ARDRegression(),
            # linear_model.SGDRegressor(),
            # # linear_model.PassiveAggressiveRegressor(loss='squared_epsilon_insensitive'),
            # linear_model.RANSACRegressor(),
            # LinearSVR(max_iter=1e4, fit_intercept=True, loss='squared_epsilon_insensitive', C=0.5),
            # SVR(max_iter=1e4, kernel='poly', C=1, degree=4),
            # SVR(max_iter=1e4, kernel='rbf', C=1, gamma=0.1),
            # SVR(kernel='linear', C=1),
            # SVR(kernel='linear', C=0.5),
            # SVR(kernel='linear', C=0.1),
            # DecisionTreeRegressor(max_depth=5),
            DecisionTreeRegressor(max_depth=4),
            DecisionTreeRegressor(max_depth=None),
            RandomForestRegressor(n_estimators=100),
            # AdaBoostRegressor(learning_rate=0.9, loss='square'),
            # BaggingRegressor(),
            MLPRegressor()
        )

        self._nn_ensemble = [ MLPRegressor(nb_epoch=1000) for i in range(5) ]  # 5 Multi Layer Perceptrons in the ensemble

        self.regressors = self._nn_ensemble

        # set regressor labels
        self.regressor_labels = []
        self.regressor_count = len(self.regressors)
        for i, regr in enumerate(self.regressors):
            self.regressor_labels.append(str(regr))

    def _dprint(self, *args, **kwargs):
        """overload print() function to only print when verbose=True."""
        if self._verbose:
            return __builtin__.print(*args, **kwargs)

    def fit(self, X_train, y_train, samples_per_regressor=None, regressor_overlap=0):
        """ Fits the model for all the regression algorithms in the ensemble.
            The models themselves can be accessed directly at EnsembleRegressor.regressors,
            and their labels is accessible in EnsembleRegressor.regressor_labels.
        :param X_train: Data matrix. Shape [# samples, # features].
        :param y_train: Target value vector.
        :param samples_per_regressor: Number of samples from X_train that each regressor will be trained on.
                                      Default 'None' will cause all regressors to be trained on all samples.
        :param regressor_overlap: If samples_per_regressor is not None, this is the number of samples overlapping for
                                  every adjacent pair of regressors. Defaults to no overlap.
        """
        start_sample = 0
        if samples_per_regressor is None:
            end_sample = -1
        else:
            end_sample = samples_per_regressor

        start = time.time()
        for i, regr in enumerate(self.regressors):
            self._dprint('## ' + str(i) + '. ' + str(regr))

            X = X_train[start_sample:end_sample, :]
            y = y_train[start_sample:end_sample]
            regr.fit(X, y)

            if samples_per_regressor is not None:
                start_sample = start_sample + samples_per_regressor - regressor_overlap
                end_sample = start_sample + samples_per_regressor

            if type(regr) in [linear_model.LinearRegression, linear_model.Ridge, LinearSVR]:
                self._dprint('\tCoefficients: ', ', '.join(['%.2f' % f for f in regr.coef_]))

            if hasattr(regr, 'alphas_'):
                self._dprint('\tAlphas: ', ', '.join(['%.2f' % f for f in regr.alphas_]))

        self._dprint('Total running time: %.2f' % (time.time() - start))

    def predict(self, X):
        """
        :param X: Data matrix. Shape [# samples, # features].
        :return: Ensemble predictions. Shape [# regressors, # samples].
        """
        Z = np.ndarray(shape=(len(self.regressors), X.shape[0]))
        for i, regr in enumerate(self.regressors):
            # zip the real and predicted values together, sort them, and unzip them
            try:
                Z[i, :] = regr.predict(X)
            except:
                print(regr)
                raise

        return Z

    def score(self, X_test, y_test):
        """
        :return: vector with the R^2 score for each regressor
        """
        s = np.zeros(self.regressor_count)
        for i, regr in enumerate(self.regressors):
            try:
                s[i] = regr.score(X_test, y_test)
            except:
                print(regr)
                raise
        return s

    def mean_squared_error(self, X_test, y_test):
        """
        :return: vector with the MSE for each regressor
        """
        # Z = self.predict(X_test)
        # return np.mean((Z - y_test[None, :])**2, 1)
        return mean_squared_error(y_test[None, :], self.predict(X_test))
        # y[None, :] ensures that the vector is properly oriented
        # np.mean(..., 1) does the mean along the columns returning regressor_count results