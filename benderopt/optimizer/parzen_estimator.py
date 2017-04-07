import numpy as np
from ..base import Parameter
from .optimizer import BaseOptimizer
from benderopt.utils import logb


def parzen_estimator_build_posterior_parameter(parameter, observations):
    """TPE algorith transform a prior parameter into a posterior parameters using observations
    to build posterior.
    """
    posterior_parameter = None
    parameter_values = [observation.sample[parameter.name] for observation in observations]
    search_space = parameter.search_space
    if parameter.category == "categorical":
        """ TODO Compare mean (current implem) vs hyperopt approach."""
        prior_probabilities = np.array(search_space["probabilities"])
        posterior_probabilities = prior_probabilities
        if len(parameter_values) != 0:
            observed_probabilities = np.array([parameter_values.count(value)
                                               for value in search_space["values"]])
            observed_probabilities = observed_probabilities / np.sum(observed_probabilities)
            posterior_probabilities += observed_probabilities
        posterior_probabilities /= sum(posterior_probabilities)

        # Build param
        posterior_parameter = Parameter.from_dict(
            {
                "name": parameter.name,
                "category": "categorical",
                "search_space": {
                    "values": search_space["values"],
                    "probabilities": list(posterior_probabilities),
                }
            }
        )

    if parameter.category in ("uniform", "normal", "loguniform", "lognormal"):
        if parameter.category == "uniform":
            prior_mu = 0.5 * (search_space["high"] + search_space["low"])
            prior_sigma = (search_space["high"] - search_space["low"])
        elif parameter.category == "loguniform":
            prior_mu = search_space["base"] ** (0.5 *
                                                (logb(search_space["high"], search_space["base"]) +
                                                 logb(search_space["low"], search_space["base"])))
            prior_sigma = search_space["base"] ** (
                logb(search_space["high"], search_space["base"]) -
                logb(search_space["low"], search_space["base"]))
        elif parameter.category in ("normal", "lognormal"):
            prior_mu = search_space["mu"]
            prior_sigma = search_space["sigma"]

        # Mus
        mus = np.sort(parameter_values + [prior_mu])

        # Sigmas
        # Trick to get for each mu the greater distance from left and right neighbor
        # when low and high are not defined we use inf to get the only available distance
        # (right neighbor for sigmas[0] and left for sigmas[-1])
        if parameter.category in ("loguniform", "lognormal"):
            tmp = np.concatenate(
                (
                    [search_space["low"]],
                    logb(mus, search_space["base"]),
                    [search_space["high"]],
                )
            )
        else:
            tmp = np.concatenate(
                (
                    [search_space.get("low", np.inf)],
                    mus if search_space.get("base") is None else logb(mus, search_space["base"]),
                    [search_space.get("high", -np.inf)],
                )
            )
        sigmas = (np.maximum(tmp[1:-1] - tmp[0:-2], tmp[2:] - tmp[1:-1])
                  if search_space.get("base") is None else
                  search_space["base"] ** np.maximum(tmp[1:-1] - tmp[0:-2], tmp[2:] - tmp[1:-1]))

        # Use formulas from hyperopt to clip sigmas
        sigma_max_value = prior_sigma
        sigma_min_value = prior_sigma / min(100.0, (1.0 + len(mus)))
        sigmas = np.clip(sigmas, sigma_min_value, sigma_max_value)

        # Fix prior sigma with correct value
        sigmas[np.where(mus == prior_mu)[0]] = prior_sigma

        posterior_parameter = Parameter.from_dict(
            {
                "name": parameter.name,
                "category": "mixture",
                "search_space": {
                    "parameters": [
                        {
                            "category": "normal",
                            "search_space": {
                                "mu": mu.tolist(),
                                "sigma": sigma.tolist(),
                                "low": search_space["low"],
                                "high": search_space["high"],
                                "step": search_space.get("step", None)
                            }
                        } if parameter.category[:3] != "log" else
                        {
                            "category": "lognormal",
                            "search_space": {
                                "mu": mu.tolist(),
                                "sigma": sigma.tolist(),
                                "low": search_space["low"],
                                "high": search_space["high"],
                                "step": search_space["step"],
                                "base": search_space["base"],
                            }
                        } for mu, sigma in zip(mus, sigmas)
                    ],
                    "weights": [1 / len(mus) for _ in range(len(mus))]
                }
            }
        )

    return posterior_parameter


class ParzenEstimator(BaseOptimizer):

    def __init__(self,
                 optimization_problem,
                 batch=None,
                 gamma=0.15,
                 number_of_candidates=100,
                 max_observation=30,
                 ):
        super(ParzenEstimator, self).__init__(optimization_problem,
                                              batch=batch)

        self.gamma = gamma
        self.number_of_candidates = number_of_candidates

    def _generate_samples(self, size):
        assert size < self.number_of_candidates

        # Retrieve self.gamma % best observations (lowest loss) observations_l
        # and worst obervations (greatest loss g) observations_g
        subsample_observations = np.choice()
        size = int(len(subsample_observations) * self.gamma)
        observations_l, observations_g = self.optimization_problem.observations_quantile(
            self.gamma)

        # Build a sample going through every parameters
        samples = [{} for _ in range(size)]
        for parameter in self.parameters:

            posterior_parameter_l = parzen_estimator_build_posterior_parameter(parameter,
                                                                               observations_l)
            posterior_parameter_g = parzen_estimator_build_posterior_parameter(parameter,
                                                                               observations_g)

            # Draw candidates from observations_l
            candidates = posterior_parameter_l.draw(self.number_of_candidates)

            # Evaluate cantidates score according to g / l taking care of zero division
            scores = (posterior_parameter_g.pdf(candidates) /
                      np.clip(posterior_parameter_l.pdf(candidates),
                              a_min=1e-16,
                              a_max=None))
            sorted_candidates = candidates[np.argsort(scores)]

            for i in range(size):
                samples[i][parameter.name] = sorted_candidates[i]

        return samples
