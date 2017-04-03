import numpy as np
from scipy import stats


def generate_samples_lognormal(mu,
                               sigma,
                               low,
                               high,
                               step=None,
                               base=10,
                               size=1,
                               ):
    """Generate sample for (truncated)(discrete)log10normal density."""

    # Draw a samples which fit between low and high (if they are given)
    a, b = (low - mu) / sigma, (high - mu) / sigma
    samples = base ** stats.truncnorm.rvs(a=a, b=b, size=size, loc=mu, scale=sigma)

    if step:
        samples = step * np.round(samples / step)

    return samples


def lognormal_cdf(samples,
                  mu,
                  sigma,
                  low,
                  high,
                  base=10,
                  ):
    """Evaluate (truncated)normal cumulated density function for each samples.

    http://mathworld.wolfram.com/GibratsDistribution.html

    From scipy:
    If X normal, log(X) = Y follow a lognormal dist if s=sigma and scale = exp(mu)
    So we infer for a base b : s = sigma * np.log(b) and scale = base ** mu
    are similar
    mu = 9.2156
    sigma = 8.457
    base = 145.2
    a = (stats.norm.rvs(size=1000000, loc=mu, scale=sigma))
    b = np.log(stats.lognorm.rvs(size=1000000, s=sigma * np.log(base), scale=base ** mu)) / np.log(base)

    plt.subplot(2, 1, 1)
    plt.hist(a, bins=5000)
    plt.subplot(2, 1, 2)
    plt.hist(b, bins=5000)
    plt.show()

    """
    parametrization = {
        's': sigma * np.log(base),
        'scale': base ** mu,
    }
    cdf_low = stats.lognorm.cdf(low, **parametrization)
    cdf_high = stats.lognorm.cdf(high, **parametrization)
    values = (stats.lognorm.cdf(samples, **parametrization) - cdf_low) / (cdf_high - cdf_low)
    values[(samples < low)] = 0
    values[(samples > high)] = 1

    return values


def lognormal_pdf(samples,
                  mu,
                  sigma,
                  low,
                  high,
                  base=10,
                  step=None
                  ):
    """Evaluate (truncated)(discrete)normal probability density function for each sample."""
    values = None
    if step is None:
        parametrization = {
            's': sigma * np.log(base),
            'scale': base ** mu,
        }
        cdf_low = stats.lognorm.cdf(low, **parametrization)
        cdf_high = stats.lognorm.cdf(high, **parametrization)
        values = stats.lognorm.pdf(samples, **parametrization) / (cdf_high - cdf_low)
        values[(samples < low) + (samples > high)] = 0

    else:
        values = (lognormal_cdf(samples + step / 2, mu=mu, sigma=sigma, low=low, high=high) -
                  lognormal_cdf(samples - step / 2, mu=mu, sigma=sigma, low=low, high=high))
    return values
