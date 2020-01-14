"""
    Abstract class for Monte Carlo integrators
    Usage:
        In order to implement a new MonteCarloFlow integrator
        it is necessary to implement (at least) two methods:
        - `_run_event`: integrand
            This function defines what to do in order to run one event
            of the Monte Carlo. It is used only for compilation, as the
            actual integration is done by the `run_event` method.
        - `_run_iteration`:
            This function defines what to do in a full iteration of the
            MonteCarlo (i.e., what to do in order to run for n_events)
"""

import time
from abc import abstractmethod, ABC
import numpy as np
import tensorflow as tf
from vegasflow.configflow import MAX_EVENTS_LIMIT


def print_iteration(it, res, error, extra="", threshold=0.1):
    """ Checks the size of the result to select between
    scientific notation and floating point notation """
    # note: actually, the flag 'g' does this automatically
    # but I prefer to choose the precision myself...
    if res < threshold:
        print(f"Result for iteration {it}: {res:.3e} +/- {error:.3e}" + extra)
    else:
        print(f"Result for iteration {it}: {res:.4f} +/- {error:.4f}" + extra)


class MonteCarloFlow(ABC):
    """
    Parameters
    ----------
        `n_dim`: number of dimensions of the integrand
        `n_events`: number of events per iteration
    """

    def __init__(self, n_dim, n_events, events_limits = MAX_EVENTS_LIMIT):
        # Save some parameters
        self.n_dim = n_dim
        self.xjac = 1.0 / n_events
        self.integrand = None
        self.event = None
        self.all_results = []
        self.n_events = n_events
        self.events_per_run = min(events_limits, n_events)

    @abstractmethod
    def _run_iteration(self):
        """ Run one iteration (i.e., `self.n_events`) of the
        Monte Carlo integration """

    @abstractmethod
    def _run_event(self, integrand, ncalls = None):
        """ Run one single event of the Monte Carlo integration """
        result = self.event()
        return result, pow(result, 2)

    def accumulate(self, accumulators):
        return accumulators[0]

    def run_event(self, **kwargs):
        """
        Runs the Monte Carlo event. This corresponds to a number of calls
        decided by the `events_per_run` variable. The variable `acc` is exposed
        in order to pass the tensor output back to the integrator in case it needs
        to accumulate.

        The main driver of this function is the `event` attribute which corresponds
        to the `tensorflor` compilation of the `_run_event` method together with the
        `integrand`.
        """
        if not self.event:
            raise RuntimeError("compile must be ran before running any iterations")
        events_left = self.n_events
        accumulators = []
        while events_left > 0:
            ncalls = min(events_left, self.events_per_run)
            result = self.event(ncalls = ncalls, **kwargs)
            accumulators.append(result)
            events_left -= self.events_per_run
        if len(accumulators) > 1:
            return self.accumulate(accumulators)
        else:
            accumulators[0]

    def compile(self, integrand, compilable=True):
        """ Receives an integrand, prepares it for integration
        and tries to compile unless told otherwise.

        Parameters
        ----------
            `integrand`: the function to integrate
        """
        if compilable:
            tf_integrand = tf.function(integrand)

            def run_event(**kwargs):
                return self._run_event(tf_integrand, **kwargs)

            self.event = tf.function(run_event)
        else:

            def run_event(**kwargs):
                return self._run_event(integrand, **kwargs)

            self.event = run_event

    def run_integration(self, n_iter, log_time=True):
        """ Runs the integrator for the chosen number of iterations
        Parameters
        ---------
            `n_iter`: number of iterations
        Returns
        -------
            `final_result`: integral value
            `sigma`: monte carlo error
        """
        for i in range(n_iter):
            # Save start time
            if log_time:
                start = time.time()

            # Run one single iteration and append results
            res, error = self._run_iteration()
            self.all_results.append((res, error))

            # Logs result and end time
            if log_time:
                end = time.time()
                time_str = f"(took {end-start} s)"
            else:
                time_str = ""
            print_iteration(i, res, error, extra=time_str)

        # Once all iterations are finished, print out
        aux_res = 0.0
        weight_sum = 0.0
        for result in self.all_results:
            res = result[0]
            sigma = result[1]
            wgt_tmp = 1.0 / pow(sigma, 2)
            aux_res += res * wgt_tmp
            weight_sum += wgt_tmp

        final_result = aux_res / weight_sum
        sigma = np.sqrt(1.0 / weight_sum)
        print(f" > Final results: {final_result.numpy():g} +/- {sigma:g}")
        return final_result, sigma
