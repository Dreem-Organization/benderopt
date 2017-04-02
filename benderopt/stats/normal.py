import numpy as np
from scipy import stats


def generate_samples_normal(mu,
                            sigma,
                            low,
                            high,
                            step=None,
                            size=1,
                            max_retry=50
                            ):
    """Generate sample for (log)(truncated)(discrete)normal density."""

    # Draw a samples which fit between low and high (if they are given)
    a, b = (low - mu) / sigma, (high - mu) / sigma
    samples = stats.truncnorm.rvs(a=a, b=b, size=size, loc=mu, scale=sigma)

    if step:
        samples = step * np.round(samples / step)

    return samples


def normal_cdf(samples,
               mu,
               sigma,
               low,
               high,
               ):
    """Evaluate (log)(truncated)normal cumulated density function for each samples.

    From scipy:
    If X normal, log(X) = Y follow a lognormal dist if s=sigma and scale = exp(mu)
    np.exp(stats.norm.rvs(size=1000000, loc=mu, scale=sigma))
    is similar to
    stats.lognorm.rvs(size=1000000, s=sigma, scale=np.exp(mu))
    """
    a, b = (low - mu) / sigma, (high - mu) / sigma
    values = stats.truncnorm.cdf(samples, a=a, b=b, loc=mu, scale=sigma)

    return values


def normal_pdf(samples,
               mu,
               sigma,
               low,
               high,
               step=None):
    """Evaluate (log)(truncated)(discrete)normal probability density function for each sample."""
    values = None
    if step is None:
        a, b = (low - mu) / sigma, (high - mu) / sigma
        values = stats.truncnorm.pdf(samples, a=a, b=b, loc=mu, scale=sigma)

    else:
        values = (normal_cdf(samples + step / 2, mu=mu, sigma=sigma, low=low, high=high) -
                  normal_cdf(samples - step / 2, mu=mu, sigma=sigma, low=low, high=high))
    return values
